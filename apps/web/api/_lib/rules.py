"""Hard-rules — warstwa deterministyczna PONAD modelem ML.

Zwraca decyzję 'keep' | 'deletable' | None (None = przepuść do modelu).
Stosujemy PRZED klasyfikatorem: jeśli reguła pasuje, nadpisuje predykcję modelu.

Źródło reguł: decyzje Leszka zapisane w memory (project_inbox_rules.md +
obserwacje z Trash review 2026-04-20).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

Decision = Literal["keep", "deletable"]


@dataclass(frozen=True)
class RuleHit:
    decision: Decision
    rule_id: str
    reason: str


# --- KEEP: oficjalne/transakcyjne — NIGDY auto-delete ---

KEEP_DOMAIN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # UWAGA: mBank NIE jest tu — kasujemy jego rutynę (decyzja Leszka 2026-06-06),
    # a maile o bezpieczeństwie chroni osobna gałąź mBank w apply_rules.
    (re.compile(r"(^|\.)santander\.", re.I), "bank_santander"),
    (re.compile(r"(^|\.)pkobp\.pl$", re.I), "bank_pko"),
    (re.compile(r"(^|\.)ingbank\.pl$", re.I), "bank_ing"),
    (re.compile(r"(^|\.)millennium(bank)?\.pl$", re.I), "bank_millennium"),
    (re.compile(r"(^|\.)unicredit\.pl$", re.I), "payment_inpost_unicredit"),
    (re.compile(r"(^|\.)allegropay\.pl$", re.I), "payment_allegropay"),
    (re.compile(r"security@vercel\.com$", re.I), "vercel_security"),
    (re.compile(r"notifications@vercel\.com$", re.I), "vercel_ops"),
    (re.compile(r"(^|\.)adwokatwolkiewicz\.pl$", re.I), "legal_kancelaria"),
    (re.compile(r"(^|\.)startedu\.pl$", re.I), "family_school"),
    (re.compile(r"(^|\.)eduindex\.pl$", re.I), "family_school_eduindex"),
    (re.compile(r"(^|\.)adejablonna\.pl$", re.I), "family_school_ade"),
    (re.compile(r"(^|\.)dobraedukacja\.edu\.pl$", re.I), "family_school_sde"),
    (re.compile(r"(^|\.)biznesradar\.pl$", re.I), "investing_biznesradar"),
    (re.compile(r"(^|\.)hycom\.pl$", re.I), "company_hycom"),
    (re.compile(r"(^|\.)autenti\.com$", re.I), "esign_autenti"),
    (re.compile(r"(^|\.)mail\.autenti\.com$", re.I), "esign_autenti_mail"),
    (re.compile(r"(^|\.)docusign\.(net|com)$", re.I), "esign_docusign"),
    (re.compile(r"(^|\.)aitinkerers\.org$", re.I), "newsletter_aitinkerers"),
    (re.compile(r"(^|\.)mail\.aitinkerers\.org$", re.I), "newsletter_aitinkerers_mail"),
    (re.compile(r"(^|\.)zus\.pl$", re.I), "gov_zus"),
    (re.compile(r"(^|\.)us\.gov\.pl$", re.I), "gov_us"),
    (re.compile(r"(^|\.)epuap\.gov\.pl$", re.I), "gov_epuap"),
    (re.compile(r"(^|\.)podatki\.gov\.pl$", re.I), "gov_podatki"),
    (re.compile(r"(^|\.)biznes\.gov\.pl$", re.I), "gov_biznes"),
    (re.compile(r"(^|\.)google\.com$", re.I), "google_official"),
    # google_search_console / google_webmaster usunięte — GSC kasujemy (decyzja Leszka
    # 2026-06-06). Maile bezpieczeństwa Google (logowanie) nadal chroni google_official.
    (re.compile(r"jskrzypkowski@outlook\.com$", re.I), "personal_skrzypkowski"),
    (re.compile(r"warsawainews@substack\.com$", re.I), "newsletter_warsawai"),
    (re.compile(r"(^|\.)moznainaczej\.edu\.pl$", re.I), "education_unconference"),
    (re.compile(r"(^|\.)malawielkafirma\.pl$", re.I), "newsletter_marek_jankowski"),
]

KEEP_SUBJECT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Stem matching — bez trailing \b, bo "faktura", "fakturę", "fakturze" muszą pasować
    (re.compile(r"\bfaktur", re.I), "kw_invoice_subject"),
    (re.compile(r"\b(invoice|receipt|paragon|rachunek)", re.I), "kw_invoice_en"),
    (re.compile(r"\btermin\s+p[łl]atn", re.I), "kw_payment_due"),
    (re.compile(r"\bdo\s+zap[łl]aty", re.I), "kw_to_pay"),
    (re.compile(r"potwierdzenie\s+p[łl]atno", re.I), "kw_payment_confirmation"),
    (re.compile(r"\bkupi[łl]e[śs]\s+i\s+zap[łl]aci[łl]e[śs]", re.I), "kw_allegro_purchase"),
    (re.compile(r"\bzam[oó]wieni", re.I), "kw_order"),
    (re.compile(r"delivery\s+status\s+notification.*fail", re.I), "kw_bounce"),
    (re.compile(r"security\s+(update|incident|alert|breach)", re.I), "kw_security_alert"),
    (re.compile(r"failed\s+(production\s+)?deployment", re.I), "kw_deploy_fail"),
    (re.compile(r"\bzmiana\s+regulaminu|aktualizuj.*dokumenty", re.I), "kw_tos_change"),
    (re.compile(r"\bPIT\s+(roczn|11|37|36|28)", re.I), "kw_pit_tax"),
    (re.compile(r"\bg[łl]osowani|\bkarta\s+do\s+g[łl]osowania", re.I), "kw_voting"),
    (re.compile(r"\b(NWZA|NWZ|WZA|ZWZA)\b|\bwalne\s+zgromadzenie|\bzgromadzenie\s+akcjonariusz|\bakcjonariusz", re.I), "kw_shareholders_meeting"),
    (re.compile(r"\bZUS\b", re.I), "kw_zus"),
    (re.compile(r"\b(pismo|decyzj|wezwani|zawiadomieni)\b.*\b(urz[ąa]d|s[ąa]d|ZUS|skarbowy)", re.I), "kw_gov_official"),
    (re.compile(r"search\s+console|indeksowani|noindex|sitemap", re.I), "kw_search_console"),
]

# Sender+subject KEEP (pusta lista — meta_ads_billing usunięty 2026-06-06,
# Meta rozliczenia reklam idą teraz do kasacji). Struktura zostaje na przyszłość.
KEEP_SENDER_SUBJECT_COMBO: list[tuple[re.Pattern[str], re.Pattern[str], str]] = []

# --- mBank: kasujemy rutynę, ALE chronimy maile o bezpieczeństwie konta ---
# Decyzja Leszka 2026-06-06: powiadomienia/wykazy/mForex = szum → kasuj.
# Siatka ochronna: logowanie, blokada, podejrzana transakcja, wyłudzenie, kody → KEEP.
BANK_SECURITY_DOMAINS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(^|\.)mbank\.pl$", re.I), "bank_mbank"),
]
SECURITY_KEEP_PAT = re.compile(
    r"bezpiecze[ńn]stw"
    r"|nowe\s+logowani|logowani\w*\s+do|zalogowa|zaloguj"
    r"|zablokowa|blokad[aey]|odblokuj"
    r"|podejrzan"
    r"|nieautoryzowan|autoryzacj"
    r"|wy[łl]udzen|oszust|phishing|skradzion|kradzie[żz]|w[łl]aman"
    r"|kod\s+(weryfikacyjn|jednorazow|autoryzacyjn|sms|do)|jednorazowe\s+has[łl]o"
    r"|zmiana\s+has[łl]a|reset\w*\s+has[łl]a|odzyskiwani\w*\s+has[łl]a"
    r"|security\s+(alert|incident|breach|warning)",
    re.I,
)

# --- HARD DELETABLE: znane śmieci kasowane PRZED regułami KEEP ---
# Te wzorce biją KEEP od słów-kluczy ("zamówienie", "indeksowanie") i KEEP-domenę,
# bo promo-nadawcy nadużywają transakcyjnego słownictwa (Temu "zamówienie").
HARD_DELETABLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Temu — wszystkie domeny (orders.temu.com, eu.temuemail.com, temu.com)
    (re.compile(r"(^|\.)temu\.com$", re.I), "promo_temu"),
    (re.compile(r"(^|\.)temuemail\.com$", re.I), "promo_temu"),
    # Meta — rozliczenia reklam (decyzja 2026-06-06: szum, historia jest w Ads Managerze)
    (re.compile(r"(^|\.)business-updates\.facebook\.com$", re.I), "promo_meta_ads_billing"),
    # Google Search Console — powiadomienia o własnej stronie (są w dashboardzie GSC)
    (re.compile(r"sc-noreply@google\.com$", re.I), "promo_gsc"),
    (re.compile(r"search-console-noreply@google\.com$", re.I), "promo_gsc"),
    (re.compile(r"(^|\.)googlewebmastercentral\.com$", re.I), "promo_gsc_webmaster"),
    # Sklepy / marketing / job-alerty
    (re.compile(r"(^|\.)news\.yves-rocher\.pl$", re.I), "promo_yves_rocher"),
    (re.compile(r"(^|\.)mail\.leroymerlin\.pl$", re.I), "promo_leroymerlin"),
    (re.compile(r"(^|\.)teatrcapitol\.pl$", re.I), "promo_teatr_capitol"),
    (re.compile(r"(^|\.)email\.microsoft\.com$", re.I), "promo_microsoft_marketing"),
    (re.compile(r"jobalerts-noreply@linkedin\.com$", re.I), "promo_linkedin_jobs"),
    (re.compile(r"(^|\.)rankmath\.com$", re.I), "promo_rankmath"),
]

# --- DELETABLE: twardy spam (legacy, sprawdzane po regułach KEEP) ---

DELETABLE_DOMAIN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(^|\.)temuemail\.com$", re.I), "promo_temu"),
    (re.compile(r"(^|\.)newsletter\.allegro\.pl$", re.I), "promo_allegro_newsletter"),
    (re.compile(r"(^|\.)info\.biedronka\.pl$", re.I), "promo_biedronka"),
    (re.compile(r"(^|\.)updates\.otomoto\.pl$", re.I), "promo_otomoto"),
    (re.compile(r"(^|\.)mail\.beehiiv\.com$", re.I), "promo_beehiiv_newsletter"),
]


def apply_rules(
    sender_email: str,
    sender_domain: str,
    subject: str,
) -> RuleHit | None:
    """Zwraca decyzję jeśli pasuje hard-rule, inaczej None."""
    sender_full = (sender_email or "").strip()
    domain = (sender_domain or "").strip().lower()
    subj = subject or ""

    # Wyciągnij sam adres z "Name" <addr@x> dla regexów z $-anchorem
    sender_addr = sender_full
    if "<" in sender_full and ">" in sender_full:
        sender_addr = sender_full.split("<", 1)[1].split(">", 1)[0].strip()

    def _match(pat: re.Pattern[str]) -> bool:
        return bool(pat.search(domain) or pat.search(sender_addr) or pat.search(sender_full))

    # 1) mBank: rutynę kasujemy, bezpieczeństwo zostaje (siatka ochronna)
    for pat, rid in BANK_SECURITY_DOMAINS:
        if _match(pat):
            if SECURITY_KEEP_PAT.search(subj):
                return RuleHit("keep", f"{rid}_security", f"bank-security keep: {rid}")
            return RuleHit("deletable", f"{rid}_routine", f"bank-routine delete: {rid}")

    # 2) HARD DELETABLE — znane śmieci, biją KEEP od słów-kluczy i KEEP-domenę
    for pat, rid in HARD_DELETABLE_PATTERNS:
        if _match(pat):
            return RuleHit("deletable", rid, f"hard-delete: {rid}")

    # 3) KEEP combo (sender+subject)
    for sender_pat, subj_pat, rid in KEEP_SENDER_SUBJECT_COMBO:
        if (sender_pat.search(sender_full) or sender_pat.search(sender_addr)) and subj_pat.search(subj):
            return RuleHit("keep", rid, f"sender+subject match: {rid}")

    # 4) KEEP by domain
    for pat, rid in KEEP_DOMAIN_PATTERNS:
        if _match(pat):
            return RuleHit("keep", rid, f"keep-domain: {rid}")

    # 5) KEEP by subject
    for pat, rid in KEEP_SUBJECT_PATTERNS:
        if pat.search(subj):
            return RuleHit("keep", rid, f"keep-subject: {rid}")

    # 6) DELETABLE domains (legacy)
    for pat, rid in DELETABLE_DOMAIN_PATTERNS:
        if pat.search(domain):
            return RuleHit("deletable", rid, f"delete-domain: {rid}")

    return None


# --- 7-day grace period dla borderline transactional ---
# Decyzja Leszka 2026-04-20: maile w kategoriach 1-8 z review Trash (Vercel,
# Meta Ads, Allegro Pay, mBank, InPost, Allegro purchase, startedu, Facebook)
# mogą być usunięte DOPIERO jeśli nieotwarte po 7 dniach.

GRACE_PERIOD_DAYS = 7


def is_in_grace_period(
    received_at: datetime | str,
    is_unread: bool,
    now: datetime | None = None,
) -> bool:
    """True jeśli mail ma <7 dni ORAZ jest nieprzeczytany — nie kasujemy."""
    if now is None:
        now = datetime.now(timezone.utc)
    if isinstance(received_at, str):
        received_at = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)
    age_days = (now - received_at).days
    return is_unread and age_days < GRACE_PERIOD_DAYS
