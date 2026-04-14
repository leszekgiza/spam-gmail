# PRD — SPAM Gmail

## Problem

Leszek dostaje codziennie dużą liczbę maili, z czego znacząca część to spam / newslettery / transakcyjne śmieci. Ręczne sprzątanie rano zajmuje czas, a "zalegający" inbox obciąża poznawczo przez cały dzień.

## Cel produktu

Autonomiczny asystent, który codziennie o 6:00 przygotowuje **czystą skrzynkę** — zostają tylko maile wymagające uwagi. System uczy się na podstawie rzeczywistych decyzji Leszka (co kasuje, co czyta, co zostawia, co archiwizuje).

## Success metrics

- **Precision ≥ 95%** na klasyfikacji `spam` (maksymalnie 5% false positive — czyli ważny mail nigdy nie przepada)
- **Recall ≥ 80%** na `spam` (80% śmieci wyłapanych)
- **Czas porannego przeglądu < 30 sekund** (1 klik = posprzątane)
- **Zero utraconych maili** — 7-dniowe okno undo + audit log
- Po 4 tygodniach: tryb `AUTO_DELETE` włączony, zero ręcznej interwencji

## Fazy wdrożenia

### Faza 0 — Bootstrap (jednorazowo)
Pobranie 12 miesięcy historii skrzynki, auto-labeling jako training set:
- w koszu / w spamie → `spam`
- przeczytane + zostawione w inbox > 30 dni → `keep` (ważne)
- przeczytane i zarchiwizowane → `keep` (ważne, ale obsłużone)
- nieprzeczytane > 14 dni + nie skasowane → ignorowane

### Faza 1 — SHADOW_MODE (tydzień 1) ⚠️
**Model TYLKO obserwuje — nie wykonuje żadnych akcji na skrzynce.**
- Cron 03:00: pobiera maile do DB
- Cron 06:00: klasyfikuje i zapisuje **prognozę** (do tabeli `decisions`), ale NIE archiwizuje, NIE kasuje, NIE zmienia labeli
- Dodatkowo zapisuje `observations` — co Leszek sam zrobił z mailem (skasował / przeczytał / zostawił / zarchiwizował)
- Na koniec tygodnia: porównanie prognoz modelu z rzeczywistymi decyzjami Leszka → raport accuracy / precision / recall
- Cel: potwierdzić że model rozumie wzorzec przed nadaniem mu uprawnień

### Faza 2 — ASSISTED_MODE (tydzień 2-4)
Model archiwizuje spam do labela `_AI_TRASH`, ale nie kasuje. Leszek rano zatwierdza (1 klik). Każda korekta → training set. Retrening tygodniowy.

### Faza 3 — AUTO_MODE (po ≥ 95% precision na korektach z 2 kolejnych tygodni)
Cron kasuje automatycznie (z 7-dniowym oknem recovery). WhatsApp: dzienny raport co skasowano.

## Non-goals

- Czytanie treści maili (tylko subject + 200-znakowy snippet + sender)
- Odpowiadanie na maile w imieniu użytkownika
- Obsługa wielu skrzynek / wielu użytkowników (single-user app)
- Mobilna aplikacja natywna (web wystarczy)
- Integracja z kalendarzem / taskami
- Trenowanie własnego modelu języka (używamy Haiku 4.5 + sklearn)

## Stakeholders

- **Użytkownik:** Leszek Giza (jedyny)
- **Developer:** Claude Code + Leszek
- **Hosting:** Vercel (darmowy plan)

## Ryzyka

| Ryzyko | Mitygacja |
|--------|-----------|
| Skasowany ważny mail | 7-dniowy label `_AI_TRASH` przed faktycznym `trash.delete` |
| Wyciek OAuth tokena | Tylko Vercel env vars, brak tokena w repo, rotacja co 90 dni |
| Halucynacja Haiku | LLM używany tylko dla `confidence < 0.7`, każda decyzja w `audit_log` z uzasadnieniem |
| Neon free tier pełen | Retencja 12 mies. + tylko snippet (200 zn.), nie pełne body |
| Vercel cron padnie | Sentry alerty + WhatsApp notification o braku aktywności 24h |
