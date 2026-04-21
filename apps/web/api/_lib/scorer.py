"""ML scorer — ładuje model sklearn z pliku i zwraca P(spam) dla maila.

Model bundlowany razem z kodem (801KB joblib).
Features budowane identycznie jak w packages/classifier/features.py.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

_MODEL_DIR = Path(__file__).resolve().parents[4] / "models"
_LOADED: dict[str, Any] = {}

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

NUMERIC_COLS = ["subject_len", "snippet_len", "age_days", "hour_received"]
KEYWORD_COLS = list(KEYWORD_PATTERNS.keys())


def _get_model():
    if "pipe" not in _LOADED:
        # Find latest model file
        files = sorted(_MODEL_DIR.glob("classifier_*.joblib"), reverse=True)
        if not files:
            return None
        data = joblib.load(files[0])
        _LOADED["pipe"] = data["pipeline"]
        _LOADED["version"] = data["version"]
    return _LOADED.get("pipe")


def score_email(
    sender_domain: str,
    subject: str,
    snippet: str,
    received_at: datetime | None,
) -> tuple[float, str] | None:
    """Zwraca (P(spam), model_version) lub None jeśli brak modelu."""
    pipe = _get_model()
    if pipe is None:
        return None

    now = datetime.now(timezone.utc)
    row = {
        "sender_domain": (sender_domain or "").lower(),
        "subject": subject or "",
        "snippet": (snippet or "")[:200],
        "subject_len": len(subject or ""),
        "snippet_len": len((snippet or "")[:200]),
        "age_days": max(0, (now - received_at).days) if received_at else 0,
        "hour_received": received_at.hour if received_at else 0,
    }
    for name, pat in KEYWORD_PATTERNS.items():
        row[name] = int(bool(pat.search(subject or "")))

    df = pd.DataFrame([row])
    proba = pipe.predict_proba(df)
    classes = list(pipe.classes_)
    spam_idx = classes.index("spam")
    p_spam = float(proba[0, spam_idx])
    return p_spam, _LOADED.get("version", "unknown")
