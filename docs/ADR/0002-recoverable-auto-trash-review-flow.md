# ADR-0002 - Recoverable Auto-Trash Review Flow

- Status: Accepted
- Date: 2026-04-24

## Context

Produkt nie ma dzialac wylacznie w trybie obserwacji. Uzytkownik akceptuje auto-trash-first, o ile:

- mail mozna odzyskac z Gmail Trash,
- wiadomo, co system zrobil,
- da sie rozroznic falszywe decyzje od poprawnych.

Jednoczesnie `TRASH` nie jest rownowazne `spam`, bo czesc maili trafia tam dopiero po obsluzeniu.

## Decision

1. Domyslny tryb pracy to Recoverable Auto-Trash.
2. `Shadow Mode` pozostaje opcjonalnym trybem diagnostycznym dla nowych modeli.
3. `Confirm` oznacza akceptacje decyzji AI bez dodatkowej zmiany w Gmailu.
4. `Restore` oznacza cofniecie decyzji AI i przywrocenie maila do Inbox.
5. Produkt rozroznia co najmniej:
   - `deletable_now`
   - `handled_done`
   - `keep_critical`
   - `read_later`
6. Do treningu nie wolno bezrefleksyjnie mapowac `TRASH -> spam`.

## Consequences

- review UI musi miec prawdziwe akcje `Confirm` i `Restore`
- feedback loop musi opierac sie na jawnych decyzjach uzytkownika
- bootstrap i trening wymagaja taksonomii lepszej niz binarne `trash = spam`
