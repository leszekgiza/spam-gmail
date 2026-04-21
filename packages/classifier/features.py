"""Feature engineering dla klasyfikatora spam/keep.

Cechy:
- sender_domain (kategoryczne)
- subject (TF-IDF uni+bi-gramy, lowercase)
- snippet (TF-IDF unigramy)
- keywords flags (regex): faktura, zwrot, reacted, newsletter, daily, weekly,
  zamówienie, kupiłeś, fwd:, re:, unsubscribe, notification, reminder
- numerical: subject_len, snippet_len, age_days, is_unread, hour_received
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import pandas as pd

KEYWORD_PATTERNS: dict[str, re.Pattern[str]] = {
    "kw_invoice": re.compile(r"\b(faktur|invoice|receipt|paragon|rachunek)", re.I),
    "kw_order": re.compile(r"\b(zam[óo]wienie|order|kupi[ae][łl]e[śs]|purchase|zap[łl]aci[łl]e[śs])", re.I),
    "kw_return": re.compile(r"\b(zwrot|refund|return)", re.I),
    "kw_delivery": re.compile(r"\b(przesy[łl]k|dostaw|delivery|shipment|tracking|track.?your)", re.I),
    "kw_social": re.compile(r"\b(reacted|liked|commented|mentioned|follow|followed)", re.I),
    "kw_newsletter": re.compile(r"\b(newsletter|daily|weekly|digest|roundup|update)", re.I),
    "kw_notification": re.compile(r"\b(notification|notified|alert|reminder)", re.I),
    "kw_unsubscribe": re.compile(r"\b(unsubscribe|opt.?out|wypisz|rezygnacj)", re.I),
    "kw_message": re.compile(r"\b(message|wiadomo[śs][ćc]|messaged|wrote)", re.I),
    "kw_reply_fwd": re.compile(r"^(re|odp|fw|fwd|pd):\s", re.I),
    "kw_verification": re.compile(r"\b(verify|verification|confirm|potwierd[źz])", re.I),
    "kw_security": re.compile(r"\b(password|login|sign.?in|security|bezpiecze[ńn]stw)", re.I),
}


def build_features(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Z listy dict z DB (raw_emails + labels) zbuduj DataFrame cech."""
    df = pd.DataFrame(rows)
    df["subject"] = df["subject"].fillna("").astype(str)
    df["snippet"] = df["snippet"].fillna("").astype(str)
    df["sender_domain"] = df["sender_domain"].fillna("").astype(str).str.lower()

    df["subject_len"] = df["subject"].str.len()
    df["snippet_len"] = df["snippet"].str.len()

    now = datetime.now(timezone.utc)
    df["received_at"] = pd.to_datetime(df["received_at"], utc=True)
    df["age_days"] = (now - df["received_at"]).dt.days.clip(lower=0)
    df["hour_received"] = df["received_at"].dt.hour

    # UWAGA: NIE używamy labels (UNREAD/INBOX/TRASH) jako cech —
    # to byłby data leakage, bo user_label='spam' pochodzi właśnie z tych labeli
    # podczas bootstrapu. W runtime nowe maile są zawsze INBOX + UNREAD.

    for name, pat in KEYWORD_PATTERNS.items():
        df[name] = df["subject"].str.contains(pat, regex=True, na=False).astype(int)

    return df


NUMERIC_COLS = [
    "subject_len", "snippet_len", "age_days", "hour_received",
]
KEYWORD_COLS = list(KEYWORD_PATTERNS.keys())
CATEGORICAL_COLS = ["sender_domain"]
TEXT_COL_SUBJECT = "subject"
TEXT_COL_SNIPPET = "snippet"
