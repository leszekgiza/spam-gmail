"""4-klasowy labeling dla ground truth — rozwiązuje 'trash ≠ spam' leakage.

Klasy:
- deletable_now         — jawny spam (newsletter, promo, social noti)
- transactional_keep    — faktury/bank/security — HARD keep, nigdy auto-delete
- archival_after_handled — user sam wyrzucił do trash PO obsłudze (nie ucz
                           tego jako 'spam' — to "cleanup", nie klasyfikacja)
- read_later            — tematyczne newslettery które user czyta wybiórczo

Input: rekord z DB (sender_domain, subject, gmail_labels, received_at, etc).
Output: jedna z 4 klas ORAZ czy rekord powinien trafić do treningu.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .rules import (
    KEEP_DOMAIN_PATTERNS,
    KEEP_SENDER_SUBJECT_COMBO,
    KEEP_SUBJECT_PATTERNS,
)

Class4 = Literal[
    "deletable_now",
    "transactional_keep",
    "archival_after_handled",
    "read_later",
]


@dataclass(frozen=True)
class LabelDecision:
    cls: Class4
    include_in_training: bool
    train_target: Literal["spam", "keep"] | None
    reason: str


READ_LATER_DOMAINS = re.compile(
    r"(substack\.com|linkedin\.com|deeplearning\.ai|strefainwestorow|"
    r"subiektywnieofinansach|biznesradar\.pl|sygna[łl]\s?ai)",
    re.I,
)


def _is_transactional(sender_email: str, sender_domain: str, subject: str) -> str | None:
    """Zwróć rule_id jeśli mail jest transakcyjny/krytyczny."""
    for sp, subp, rid in KEEP_SENDER_SUBJECT_COMBO:
        if sp.search(sender_email) and subp.search(subject):
            return rid
    for pat, rid in KEEP_DOMAIN_PATTERNS:
        if pat.search(sender_domain) or pat.search(sender_email):
            return rid
    for pat, rid in KEEP_SUBJECT_PATTERNS:
        if pat.search(subject):
            return rid
    return None


def derive_label(
    sender_email: str,
    sender_domain: str,
    subject: str,
    gmail_labels: list[str],
    user_label: str | None = None,
) -> LabelDecision:
    """Wyprowadź 4-klasową etykietę z kontekstu bootstrap'owego.

    user_label: historyczna binarna etykieta ('spam'/'keep') z bootstrapu —
    używamy jej jako domyślnej gdy reguły nie strzelają.
    """
    labels = set(l.upper() for l in gmail_labels or [])
    in_trash = "TRASH" in labels
    in_inbox = "INBOX" in labels
    is_unread = "UNREAD" in labels

    tx_rule = _is_transactional(sender_email, sender_domain, subject)

    # 1) Transactional w TRASH → archival_after_handled (NIE ucz jako spam)
    if tx_rule and in_trash:
        return LabelDecision(
            cls="archival_after_handled",
            include_in_training=False,
            train_target=None,
            reason=f"trash+transactional ({tx_rule}) — user cleanup, exclude",
        )

    # 2) Transactional w INBOX → HARD keep (silny positive sample)
    if tx_rule:
        return LabelDecision(
            cls="transactional_keep",
            include_in_training=True,
            train_target="keep",
            reason=f"transactional ({tx_rule})",
        )

    # 3) Read-later — tematyczne; nie ucz auto-spam, chyba że w TRASH już ≥30 dni
    if READ_LATER_DOMAINS.search(sender_domain) or READ_LATER_DOMAINS.search(sender_email):
        if in_trash:
            return LabelDecision(
                cls="deletable_now",
                include_in_training=True,
                train_target="spam",
                reason="read_later + trash → treat as spam signal",
            )
        return LabelDecision(
            cls="read_later",
            include_in_training=False,
            train_target=None,
            reason="tematic newsletter — user reads selectively",
        )

    # 4) Fallback do historycznej etykiety z bootstrapu
    if user_label == "spam" or (in_trash and not in_inbox):
        return LabelDecision(
            cls="deletable_now",
            include_in_training=True,
            train_target="spam",
            reason="trash-derived spam",
        )
    return LabelDecision(
        cls="transactional_keep" if tx_rule else "deletable_now",
        include_in_training=True,
        train_target="keep",
        reason="default keep",
    )
