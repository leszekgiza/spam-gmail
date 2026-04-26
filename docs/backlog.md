# Backlog - SPAM Gmail

Priorytety: `M` = Must, `S` = Should, `C` = Could.

## Epic 1 - Contract Closure

- [x] `M` Ustalic, ze domyslny tryb produktu to Recoverable Auto-Trash
- [x] `M` Zdefiniowac `Shadow Mode` jako tryb diagnostyczny, a nie domyslny rollout
- [x] `M` Zdefiniowac `Confirm` i `Restore`
- [x] `M` Zdefiniowac, ze nie kazdy `TRASH` oznacza `spam`
- [x] `M` Wybrac jeden runtime: `apps/web`
- [x] `M` Udokumentowac kontrakt architektury i danych

## Epic 2 - Runtime Consolidation

- [ ] `M` Usunac `apps/api` z kanonicznej sciezki deploymentu
- [ ] `M` Miec jedna kopie regul i klasyfikacji w `packages/*`
- [ ] `M` Usunac duplikaty `_lib/rules.py`, `_lib/gmail_client.py`, `_lib/db.py`
- [ ] `S` Uporzadkowac nazwy endpointow cron, zeby odpowiadaly faktycznej roli

## Epic 3 - Correct Review Flow

- [ ] `M` Cron ma zapisywac `decisions`, nie training labels
- [ ] `M` Cron ma logowac automatyczne akcje do `audit_log`
- [ ] `M` `GET /api/review` ma czytac pending decisions
- [ ] `M` `POST restore` ma naprawde przywracac mail w Gmailu
- [ ] `M` `POST confirm` ma zapisywac jawne potwierdzenie ludzkie
- [ ] `M` Dodac auth do review UI/API

## Epic 4 - Ground Truth i Training Data

- [ ] `M` Wdrozyc 4-klasowa taksonomie ground truth
- [ ] `M` Rozdzielic `deletable_now` od `handled_done`
- [ ] `M` Wykluczyc `handled_done` i `read_later` z prostego binarnego `trash = spam`
- [ ] `M` Trening ma korzystac tylko z curated bootstrap + explicit human feedback
- [ ] `S` Dodac weekly evaluation precision / recall / restore-rate

## Epic 5 - Safety i Operations

- [ ] `M` Kazda automatyczna akcja musi miec audit trail
- [ ] `M` Naprawic lokalne i produkcyjne zarzadzanie sekretami
- [ ] `S` Dodac monitoring / alerting
- [ ] `S` Dodac diagnostyczny `Shadow Mode` dla nowych modeli

## Epic 6 - Later Automation

- [ ] `C` Dodac LLM fallback tylko dla naprawde niepewnych przypadkow
- [ ] `C` Dodac weekly retraining automation
- [ ] `C` Rozwazyc osobny auto-purge dopiero po stabilnych metrykach

## Out of Scope

- multi-user
- mobile native app
- pelne body maili
- odpisywanie na maile
- kalendarz / tasks
