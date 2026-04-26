# ADR-0001 - Canonical Runtime and Data Contract

- Status: Accepted
- Date: 2026-04-24

## Context

Repo zawiera rownolegle `apps/web` i `apps/api`, zdublowane moduły `_lib/*` oraz rozjechana semantyke tabel `decisions`, `observations`, `feedback` i `audit_log`.

Bez jednej definicji runtime i danych nie da sie wiarygodnie rozwijac review flow ani feedback loop.

## Decision

1. Kanoniczny runtime produkcyjny to `apps/web`.
2. `apps/web/app` jest miejscem dla UI i Next API.
3. `apps/web/api` jest miejscem dla Python Vercel Functions.
4. `packages/*` jest jedynym zrodlem wspolnej logiki.
5. `apps/api` zostaje uznane za legacy path do wygaszenia.
6. Semantyka tabel:
   - `raw_emails` = snapshot danych Gmail
   - `decisions` = decyzje modelu i regul
   - `observations` = pasywne obserwacje stanu skrzynki
   - `feedback` = tylko jawne ludzkie sygnaly
   - `audit_log` = automatyczne akcje systemu

## Consequences

- review UI i cron beda oparte o ten sam kontrakt
- automatyczne akcje nie moga same zasilać `feedback`
- trzeba usunac duplikaty kodu z `apps/api/_lib` i `apps/web/api/_lib`
- trzeba przepiac implementacje review na `decisions` + `feedback` + `audit_log`
