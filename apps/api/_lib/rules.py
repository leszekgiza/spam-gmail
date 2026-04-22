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
    (re.compile(r"(^|\.)mbank\.pl$", re.I), "bank_mbank"),
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
    (re.compile(r"(^|\.)zus\.pl$", re.I), "gov_zus"),
    (re.compile(r"(^|\.)us\.gov\.pl$", re.I), "gov_us"),
    (re.compile(r"(^|\.)epuap\.gov\.pl$", re.I), "gov_epuap"),
    (re.compile(r"(^|\.)podatki\.gov\.pl$", re.I), "gov_podatki"),
    (re.compile(r"(^|\.)biznes\.gov\.pl$", re.I), "gov_biznes"),
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
    (re.compile(r"\bZUS\b", re.I), "kw_zus"),
    (re.compile(r"\b(pismo|decyzj|wezwani|zawiadomieni)\b.*\b(urz[ąa]d|s[ąa]d|ZUS|skarbowy)", re.I), "kw_gov_official"),
]

# Sender-from patterns (for senders like noreply@business-updates.facebook.com
# gdzie subject może nie mieć słowa 'faktura' ale treść to rozliczenie reklam)
KEEP_SENDER_SUBJECT_COMBO: list[tuple[re.Pattern[str], re.Pattern[str], str]] = [
    (re.compile(r"business-updates\.facebook\.com$", re.I),
     re.compile(r"potwierdzenie\s+p[łl]atno|transakcj", re.I),
     "meta_ads_billing"),
]

# --- DELETABLE: twardy spam ---

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

    # KEEP combo (sender+subject)
    for sender_pat, subj_pat, rid in KEEP_SENDER_SUBJECT_COMBO:
        if sender_pat.search(sender_full) and subj_pat.search(subj):
            return RuleHit("keep", rid, f"sender+subject match: {rid}")

    # KEEP by domain
    for pat, rid in KEEP_DOMAIN_PATTERNS:
        if pat.search(domain) or pat.search(sender_full):
            return RuleHit("keep", rid, f"keep-domain: {rid}")

    # KEEP by subject
    for pat, rid in KEEP_SUBJECT_PATTERNS:
        if pat.search(subj):
            return RuleHit("keep", rid, f"keep-subject: {rid}")

    # DELETABLE domains
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
