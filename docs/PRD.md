# PRD - SPAM Gmail

## Problem

Inbox zawiera mieszanke waznych maili, rzeczy do przeczytania pozniej, newsletterow, powiadomien i zwyklych smieci. Reczne sprzatanie rano zabiera czas i obciaza poznawczo.

## Cel produktu

Zbudowac jednoosobowego asystenta Gmail, ktory:

- automatycznie usuwa z pola widzenia oczywiste smieci,
- nie gubi waznych wiadomosci,
- pozwala szybko cofnac falszywe decyzje,
- uczy sie na rzeczywistych decyzjach uzytkownika.

## Domyslny tryb produktu

Domyslny tryb to **Recoverable Auto-Trash**.

To znaczy:

- system moze automatycznie przenosic wybrane maile do Gmail Trash,
- Gmail Trash jest buforem bezpieczenstwa i miejscem odzyskania,
- rano uzytkownik moze przejrzec decyzje AI i je skorygowac.

## Co oznacza Shadow Mode

`Shadow Mode` to tryb, w ktorym system:

- zapisuje przewidywania,
- nic nie zmienia w Gmailu,
- sluzy tylko do walidacji nowego modelu albo nowych regul.

`Shadow Mode` nie jest glownym trybem wdrozenia dla tego produktu. To tryb diagnostyczny.

## Kluczowe pojecia produktu

### Restore

`Restore` oznacza:

- przywroc mail z Gmail Trash do Inbox,
- zapisz jawny ludzki sygnal, ze decyzja AI byla bledna,
- uzyj tego jako feedback `keep`.

### Confirm

`Confirm` oznacza:

- uzytkownik potwierdza, ze AI miala racje,
- mail zostaje w Gmail Trash,
- brak dodatkowej zmiany w Gmailu,
- zapisujemy jawny ludzki sygnal poprawnej decyzji AI jako feedback `spam`.

`Confirm` nie oznacza trwalego skasowania. To akceptacja decyzji AI.

## Ground truth

Nie kazdy mail w `TRASH` oznacza spam. Produkt musi rozrozniac co najmniej 4 klasy:

1. `deletable_now`
   Mail niechciany juz teraz: promo, social noise, newsletter-smiec, oczywisty spam.
2. `handled_done`
   Mail byl przydatny, ale po obsluzeniu nie jest juz potrzebny w Inbox.
3. `keep_critical`
   Mail wazny lub ryzykowny do utraty: finanse, prawo, security, urzedy, istotne transakcje.
4. `read_later`
   Mail, ktory bywa czytany wybiorczo i nie powinien automatycznie trafic do kosza.

## Zasady treningu

- `deletable_now` moze byc uczone jako `spam`
- `keep_critical` moze byc uczone jako `keep`
- `handled_done` nie moze byc automatycznie traktowane jako `spam`
- `read_later` nie powinno byc domyslnie traktowane jako `spam`
- do treningu po rolloutcie trafiaja tylko jawne sygnaly ludzkie oraz ostroznie przygotowany bootstrap

## Success metrics

- precision dla auto-trash >= 95%
- falszywe auto-trash sa odzyskiwalne z Gmail Trash
- poranny review < 60 sekund
- 100% automatycznych akcji ma audit trail
- model nie uczy sie na wlasnych decyzjach bez ludzkiego potwierdzenia

## Zakres biezacej wersji

### In scope

- single-user app
- Gmail metadata: sender, domain, subject, snippet
- auto-trash dla bezpiecznych przypadkow
- review queue z `Restore` i `Confirm`
- feedback loop oparty o jawne decyzje uzytkownika

### Out of scope

- pelne czytanie body maili
- odpisywanie na maile
- multi-user
- mobile native app
- kalendarz / taski

## Ryzyka i mitygacje

| Ryzyko | Mitygacja |
|--------|-----------|
| Wazny mail trafia do Trash | `Restore`, audit log, ostroznosc w danych treningowych |
| Model myli `handled_done` ze spamem | 4-klasowa taksonomia ground truth |
| System uczy sie na swoich decyzjach | `feedback` tylko dla jawnych sygnalow ludzkich |
| Architektura rozjezdza sie z implementacja | jeden runtime, jedna kopia regul, jedna semantyka tabel |

## Roadmap produktu

### Etap 1 - Contract Closure

- ustalic jeden runtime
- ustalic jedna semantyke `decisions`, `observations`, `feedback`, `audit_log`
- ustalic semantyke `Restore` i `Confirm`

### Etap 2 - Correct Review Flow

- prawdziwe `Restore` w Gmailu
- review queue oparte o `decisions`, nie o historyczne `feedback`
- audit kazdej automatycznej akcji

### Etap 3 - Data Quality i Retraining

- poprawny bootstrap bez `trash = spam`
- trening tylko na danych, ktore wolno traktowac jako ground truth
- raporty precision / recall

### Etap 4 - Optional Shadow Validation i Further Automation

- `Shadow Mode` tylko do testu nowych modeli
- ewentualny auto-purge dopiero po stabilnych metrykach
