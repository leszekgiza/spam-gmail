# Backlog — SPAM Gmail

Priorytety: **M** = Must, **S** = Should, **C** = Could, **W** = Won't (for now).

## Epic 1: Foundation (Sesja 1) — IN PROGRESS

- [x] **M** Monorepo scaffold (Turborepo + Next.js + Python)
- [x] **M** `vercel.ts` z cron schedule
- [x] **M** GitHub repo `leszekgiza/spam-gmail` (public)
- [x] **M** GitHub Actions CI (lint + typecheck + Python compile)
- [x] **M** Dokumentacja lekka: PRD, HLD, backlog
- [ ] **M** Neon DB provisioning + `migrate.sql` zaaplikowany
- [ ] **M** Vercel link + first deploy (placeholder)
- [ ] **S** Threat model + privacy doc
- [ ] **S** ADR-0001 (stack), ADR-0002 (archive-not-delete)

## Epic 2: Gmail integracja (Sesja 2)

- [ ] **M** Google Cloud project + OAuth client
- [ ] **M** `packages/gmail/auth.py` — OAuth flow + refresh token
- [ ] **M** `packages/gmail/operations.py` — fetch, archive, label, batch delete
- [ ] **M** `scripts/bootstrap_history.py` — pobierz 12 mies., auto-labeling
- [ ] **M** Migracja bootstrap → Neon (`raw_emails` + `feedback` source='bootstrap')
- [ ] **S** Rate limiting / retry logic (Gmail API quota)

## Epic 3: SHADOW_MODE — tydzień 1 obserwacji (Sesja 3)

- [ ] **M** `packages/classifier/features.py` — feature engineering
  - sender domain, czy kontakt w książce, średnia historia z nadawcą
  - keywords w subject (regex + TF-IDF na snippet)
  - time of day, day of week
  - is_newsletter (unsubscribe header), is_transactional
- [ ] **M** `packages/classifier/model.py` — sklearn LogisticRegression + GradientBoosting
- [ ] **M** `packages/classifier/train.py` — trenuj na bootstrap
- [ ] **M** `cron/classify.py` — w shadow mode: tylko INSERT decisions
- [ ] **M** `cron/observe.py` (23:00) — zapisz co Leszek zrobił z każdym mailem
- [ ] **M** `scripts/weekly_report.py` — porównaj decisions vs observations
- [ ] **S** Raport na WhatsApp w niedzielę: "Model miał accuracy X% w tym tygodniu"

## Epic 4: ASSISTED_MODE + Web UI (Sesja 4)

- [ ] **M** `packages/classifier/llm.py` — Haiku 4.5 dla confidence < 0.7
- [ ] **M** `cron/classify.py` — archiwizacja do `_AI_TRASH` gdy `SHADOW_MODE=false`
- [ ] **M** `apps/web/app/page.tsx` — lista decyzji + checkboxy + 3 przyciski
- [ ] **M** `apps/api/review/confirm.py` — batch delete zaznaczonych
- [ ] **M** `apps/api/review/restore.py` — restore + feedback INSERT
- [ ] **M** WhatsApp notification po cronie
- [ ] **S** Pokaż w UI: decyzja + confidence + (jeśli LLM) reasoning
- [ ] **S** Autentykacja (Sign in with Vercel? Email link?)
- [ ] **C** Dark mode / accessibility

## Epic 5: Feedback loop + retrening (Sesja 5)

- [ ] **M** `scripts/retrain.py` — cotygodniowy retrening
- [ ] **M** Eval harness — accuracy/precision/recall per model version
- [ ] **M** Promocja modelu tylko jeśli ≥ baseline (BLUE/GREEN)
- [ ] **M** Kill switch test: ustawienie `EMERGENCY_STOP=true` natychmiast zatrzymuje cron
- [ ] **S** Vercel Analytics — dashboard metryk
- [ ] **S** Sentry integracja — alerty na błędy
- [ ] **C** A/B test: Haiku vs Sonnet na niepewnych

## Epic 6: AUTO_MODE (Sesja 6+)

- [ ] **M** Decyzja przejścia w `AUTO_DELETE=true` (po 2 tyg. ≥95% precision)
- [ ] **M** `cron/purge.py` — trwałe kasowanie po 7 dniach
- [ ] **S** Dzienny WhatsApp: "Dziś skasowano N maili, X false positives"

## Backlog — Won't (dla tego projektu)

- **W** Multi-user support
- **W** Mobile app
- **W** Kalendar / Tasks integracja
- **W** Własny fine-tuned LLM
- **W** Czytanie pełnego body maili
