# HLD - SPAM Gmail

## Canonical architecture

Od 2026-04-24 kanoniczna architektura jest nastepujaca:

| Obszar | Kanoniczna lokalizacja | Rola |
|--------|-------------------------|------|
| Web UI | `apps/web/app` | poranny review |
| Review API | `apps/web/app/api` | kolejka review i akcje uzytkownika |
| Python cron functions | `apps/web/api` | Gmail automation |
| Shared Python modules | `packages/*` | jedna kopia regul i logiki wspolnej |
| Legacy runtime | `apps/api` | do wycofania z aktywnej sciezki deploymentu |

## Zasady architektoniczne

1. Jest jeden runtime produkcyjny: `apps/web`.
2. Jest jedna kanoniczna kopia regul i klasyfikacji: `packages/*`.
3. `apps/api` nie jest miejscem na nowy kod i ma zostac wygaszony.
4. Review UI i cron musza operowac na tym samym modelu danych.

## Logical flow

### 1. Decision pass

- cron pobiera maile z Gmaila
- zapisuje snapshot do `raw_emails`
- hard-rules i model ML podejmuja decyzje
- decyzja trafia do `decisions`
- jesli decyzja to auto-trash, akcja trafia do `audit_log` i jest wykonywana w Gmailu

### 2. Morning review

- UI pobiera tylko te decyzje, ktore wymagaja review albo nie maja jeszcze jawnego feedbacku
- `Restore` przywraca mail do Inbox i zapisuje ludzki feedback `keep`
- `Confirm` nie zmienia Gmaila, ale zapisuje ludzki feedback `spam`

### 3. Learning loop

- trening korzysta z curated bootstrap + explicit human feedback
- automatyczne akcje systemu nie sa same w sobie training labels

## Data contract

| Tabela | Znaczenie |
|--------|-----------|
| `raw_emails` | snapshot metadanych Gmail potrzebny do klasyfikacji i review |
| `decisions` | kazda decyzja AI/systemu przed lub w trakcie wykonania akcji |
| `observations` | pasywna obserwacja finalnego stanu skrzynki; material diagnostyczny, nie jawny feedback |
| `feedback` | tylko jawne sygnaly ludzkie, np. `restore`, `confirm`, reczne oznaczenie |
| `audit_log` | kazda automatyczna akcja wykonana przez system na Gmailu |

## Semantyka tabel

### `decisions`

Powinna zawierac:

- decyzje modelu lub hard-rule,
- confidence,
- model version / rule id,
- informacje, czy akcja zostala wykonana,
- timestamp.

### `observations`

To material pomocniczy:

- sluzy do diagnostyki,
- moze sluzyc do porownan model vs rzeczywistosc,
- nie zastapi jawnego feedbacku uzytkownika.

### `feedback`

To jest tabela z najsilniejszym sygnalem. Powinna zawierac tylko:

- `user_restore -> keep`
- `user_confirm -> spam`
- reczne bootstrapowe etykiety, o ile sa jawnie dopuszczone do treningu

Automatyczny cron nie powinien wpisywac do `feedback` tylko dlatego, ze sam cos przeniosl do Trash.

### `audit_log`

To dziennik dzialan systemu:

- auto-trash,
- restore wykonany przez API,
- ewentualny future purge.

## Review semantics

### `Restore`

- Gmail mutation: tak
- efekt: `TRASH -> INBOX`
- zapis do `feedback`: tak
- znaczenie: AI sie pomylila

### `Confirm`

- Gmail mutation: nie
- efekt: mail zostaje w Trash
- zapis do `feedback`: tak
- znaczenie: AI miala racje

## Deployment contract

Jeden Vercel project powinien byc zrootowany w `apps/web`.

To oznacza:

- Next.js UI i review API sa wdrazane z `apps/web`
- Python cron functions sa wdrazane z `apps/web/api`
- nie utrzymujemy rownolegle `apps/api` jako drugiej kanonicznej sciezki

## Legacy debt do zamkniecia

- usunac zdublowane reguly w `apps/web/api/_lib` i `apps/api/_lib`
- usunac aktywna zaleznosc od `apps/api`
- przestawic review na `decisions` zamiast na historyczne `feedback`
- przestac traktowac `TRASH` jako rownowaznik `spam`
