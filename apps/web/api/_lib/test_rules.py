"""Testy precedencji hard-rules. Uruchom: python apps/web/api/_lib/test_rules.py

Brak pytest w projekcie — prosty runner z assertami. Zwraca exit code != 0 przy
awarii (nadaje się do CI). Chroni przed regresją: incydenty FP (kasowanie maili
KEEP) brały się z braku takich testów — patrz memory incident_keep_rules_fp.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # api/ dla `from _lib...`
from _lib.rules import apply_rules  # noqa: E402

# (sender, domain, subject, oczekiwana_decyzja) — "keep" | "deletable" | "none"
CASES: list[tuple[str, str, str, str]] = [
    # --- mBank: rutyna kasowana, bezpieczeństwo chronione (siatka ochronna) ---
    ("mBank <kontakt@mbank.pl>", "mbank.pl", "mBank - powiadomienie e-mail", "deletable"),
    ("mBank <kontakt@mbank.pl>", "mbank.pl", "Połączenie rachunków mForex z identyfikatorem", "deletable"),
    ("mBank <kontakt@mbank.pl>", "mbank.pl", "Nowe logowanie do serwisu mBank", "keep"),
    ("mBank <kontakt@mbank.pl>", "mbank.pl", "Podejrzana transakcja na Twoim koncie", "keep"),
    ("mBank <kontakt@mbank.pl>", "mbank.pl", "Zablokowaliśmy Twoją kartę", "keep"),
    ("mBank <kontakt@mbank.pl>", "mbank.pl", "Twój kod jednorazowy do autoryzacji przelewu", "keep"),
    # --- Hard-delete znanych śmieci, bije KEEP od słów-kluczy ---
    ("Temu <temu@orders.temu.com>", "orders.temu.com", "Twoje zamówienie Temu jest w trakcie doręczenia", "deletable"),
    ("Temu <temu@eu.temuemail.com>", "eu.temuemail.com", "Twoje wcześniejsze zamówienia mogą się kwalifikować", "deletable"),
    ("Meta for Business <noreply@business-updates.facebook.com>", "business-updates.facebook.com",
     "Potwierdzenie płatności za reklamy Meta", "deletable"),
    ("Google Search Console Team <sc-noreply@google.com>", "google.com",
     "Nowe przyczyny uniemożliwiają indeksowanie stron", "deletable"),
    ("LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>", "linkedin.com", "Chief Innovation Officer", "deletable"),
    # --- Bezpieczeństwo Google (logowanie) MUSI zostać mimo że GSC kasujemy ---
    ("Google <no-reply@accounts.google.com>", "accounts.google.com", "Nowe logowanie na Twoje konto Google", "keep"),
    # --- Realne zakupy/faktury/rodzina/banki — NIGDY nie kasujemy ---
    ("Allegro <powiadomienia@allegro.pl>", "allegro.pl", "Kupiłeś i zapłaciłeś: Toster Bosch", "keep"),
    ("Apple <no_reply@email.apple.com>", "email.apple.com", "Twoja faktura z firmy Apple", "keep"),
    ("Karolina Baurycza <karolina.baurycza@adejablonna.pl>", "adejablonna.pl", "Re: Spotkanie", "keep"),
    ("Santander <kontakt@santander.pl>", "santander.pl", "powiadomienie", "keep"),
    ("Janusz Skrzypkowski <jskrzypkowski@outlook.com>", "outlook.com", "RE: ZWZA 15.05.2026", "keep"),
    ("Marii-Liisi Makara via Docusign <dse@eumail.docusign.net>", "eumail.docusign.net",
     "Complete with Docusign: Umowa", "keep"),
    ("And Tech Andrzej Skłudzki <biuro@andtech.pl>", "andtech.pl", "Oferta wspolpracy", "keep"),
    ("Aleksandra Zaborowska <aleksandra.zaborowska@poczta.onet.pl>", "poczta.onet.pl",
     "Re: spotkanie", "keep"),
    # ...ale reszta poczta.onet.pl NIE jest whitelistowana (freemail)
    ("Ktos Inny <ktos.inny@poczta.onet.pl>", "poczta.onet.pl", "Promocja tygodnia", "none"),
    # --- Regresja 2026-08-18: silnik skasowal polise Warty i RODO Uniqa ---
    ("Warta <TwojeUbezpieczenie@warta.pl>", "warta.pl",
     "Polisa - potwierdzenie zawarcia umowy ubezpieczenia", "keep"),
    ("Warta <TwojeUbezpieczenie@warta.pl>", "warta.pl",
     "Oferta ubezpieczenia - Zatwierdz do 16.08.2026", "keep"),
    ("UNIQA <propozycja@uniqa.pl>", "uniqa.pl",
     "Informacje dotyczace przetwarzania danych osobowych", "keep"),
    ("Link4 <polisa_mieszkanie@link4.pl>", "link4.pl", "Polisa mieszkaniowa: M29827089004", "keep"),
    # --- Regresja 2026-08-21: silnik skasowal dokumentacje wyjazdu do Rzymu ---
    ("Wizz Air Customer Service <notifications@notifications.wizzair.com>", "notifications.wizzair.com",
     "Important Information about your Wizz Air flight! (ER6J8X)", "keep"),
    ("\"travel document\" <noreply@doc.mail.amadeus.com>", "doc.mail.amadeus.com",
     "GIZA/LESZEK MR 22AUG2026", "keep"),
    ("SAN GIOVANNI APARTMENT 80 MQ za posrednictwem Booking.com <noreply@booking.com>", "booking.com",
     "Masz wiadomosc od obiektu SAN GIOVANNI APARTMENT 80 MQ", "keep"),
    ("LOT Polish Airlines <no-reply@preflight.lot.com>", "preflight.lot.com",
     "It's time to check-in. Check reservation", "keep"),
    ("Wizz Air <offers@noreply.wizznews.com>", "noreply.wizznews.com", "Czas na odprawe!", "keep"),
    ("Spaceship <receipts@spaceship.com>", "spaceship.com",
     "Spaceship order summary #9ff8b79b", "keep"),
    ("SolarUp <kontakt@solarup.pl>", "solarup.pl", "Fotowoltaika - porownanie wariantow", "keep"),
    # ...marketing przewoznikow NIE jest whitelistowany
    ("Wizz Air <travel@travel.wizznews.com>", "travel.wizznews.com", "Tego lata lataj juz od 129 zl", "none"),
    ("Miles & More <no-reply@milesandmore.lot.com>", "milesandmore.lot.com", "najMILszy poniedzialek", "none"),
    # --- Audyt bazy 2026-08-21: ML p0.98 kasowal dokumenty urzedowe/medyczne ---
    ("Profil Zaufany <powiadomienia@pz.gov.pl>", "pz.gov.pl", "Dokument zostal podpisany", "keep"),
    ("Profil Zaufany <powiadomienia@pz.gov.pl>", "pz.gov.pl",
     "Twoje haslo w profilu zaufanym zostalo zmienione", "keep"),
    ("mojeDR <noreply@noreply.mydr.pl>", "noreply.mydr.pl", "Link do platnosci za uslugi medyczne", "keep"),
    ("Stoen Operator <kontakt@stoen.pl>", "stoen.pl", "OWE001349955 RE: Wniosek o potwierdzenie", "keep"),
    ("Anthropic <noreply@mail.anthropic.com>", "mail.anthropic.com",
     "Your secure link to Claude.ai is here", "keep"),
    # --- Regresja: pełny header "Name" <addr> musi matchować $-anchor reguły ---
    ('"Warsaw.AI News Team" <warsawainews@substack.com>', "substack.com", "Warsaw.AI News", "keep"),
]


def main() -> int:
    fails = 0
    for sender, domain, subject, expected in CASES:
        hit = apply_rules(sender, domain, subject)
        got = hit.decision if hit else "none"
        status = "OK " if got == expected else "XXX"
        if got != expected:
            fails += 1
        rid = hit.rule_id if hit else "-"
        print(f"{status} exp={expected:9s} got={got:9s} [{rid:24s}] {subject[:46]}")
    print(f"\n{len(CASES) - fails}/{len(CASES)} OK")
    if fails:
        print(f"FAIL: {fails} przypadków nie przeszło")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
