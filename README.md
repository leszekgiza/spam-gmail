# SPAM Gmail - AI Inbox Cleaner

Jednouzytkownikowy system do automatycznego sprzatania Gmaila z bezpiecznym oknem odzyskania.

## Jak projekt ma dzialac

Tryb docelowy na dzis to **Recoverable Auto-Trash**:

1. Rano cron skanuje nowe maile w Gmailu.
2. Hard-rules i model ML wybieraja maile, ktore mozna od razu przeniesc do Gmail Trash.
3. Kazda taka decyzja jest zapisana i mozliwa do audytu.
4. Rano w UI widzisz kolejke review.
5. Dla kazdego maila mozesz zrobic:
   - `Restore` - przywroc mail z Trash do Inbox i oznacz decyzje AI jako false positive.
   - `Confirm` - potwierdz, ze AI miala racje; mail zostaje w Trash, bez dodatkowej zmiany w Gmailu.
6. Tylko jawne ludzkie korekty i potwierdzenia zasilaja feedback do treningu.

## Co NIE jest domyslnym trybem

`Shadow Mode` oznacza: system tylko przewiduje, ale nie dotyka skrzynki. To zostaje jako opcjonalny tryb diagnostyczny do walidacji nowych modeli, a nie glowna sciezka rolloutu.

## Aktualny kontrakt architektury

- **Canonical deploy root:** `apps/web`
- **Web UI:** `apps/web/app`
- **Review API:** `apps/web/app/api`
- **Python cron functions:** `apps/web/api`
- **Shared source of truth:** `packages/*`
- **Legacy path do wygaszenia:** `apps/api`

## Ground truth

Nie kazdy mail w `TRASH` oznacza spam. Produkt rozroznia co najmniej 4 klasy:

- `deletable_now` - mail niechciany, mozna go od razu przeniesc do Trash
- `handled_done` - mail byl potrzebny, ale po obsluzeniu nie musi zostac w Inbox
- `keep_critical` - mail wazny, nie wolno go auto-przenosic do Trash
- `read_later` - mail do selektywnego czytania, nie powinien byc domyslnie uczony jako spam

## Dokumentacja

- [PRD](docs/PRD.md)
- [HLD](docs/HLD.md)
- [Backlog](docs/backlog.md)
- [ADR-0001](docs/ADR/0001-canonical-runtime-and-data-contract.md)
- [ADR-0002](docs/ADR/0002-recoverable-auto-trash-review-flow.md)

## Repo

```text
apps/web/        Next.js UI + review API + Python cron functions
apps/api/        legacy runtime do usuniecia z kanonicznej sciezki
packages/        classifier, gmail, shared
scripts/         bootstrap, obserwacje, trening, narzedzia lokalne
docs/            PRD, HLD, backlog, ADR
```

## Status

Repo jest na etapie dzialajacego prototypu z aktywnym auto-trash-first, ale przed runtime consolidation i przed domknieciem poprawnego feedback loop.
