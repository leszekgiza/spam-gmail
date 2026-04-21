"""Vercel Cron: codzienne auto-czyszczenie skrzynki — hard-rules + grace period.

Uruchamiane przez Vercel Cron (patrz vercel.ts) o 4:00 UTC = 6:00 Warsaw (CEST).
W czasie zimowym (CET) to 5:00 Warsaw — do akceptacji.

Endpoint: GET/POST /api/cron/purge
Header: Authorization: Bearer $CRON_SECRET (automatycznie wstrzykiwany przez Vercel Cron)

Tryb podglądu: ?dry=1 (albo env DRY_RUN=1) — nic nie kasuje, zwraca plan.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Dodaj katalog api/ do sys.path (o jeden wyżej), żeby można było `from _lib import ...`
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from _lib.rules import (  # noqa: E402
    GRACE_PERIOD_DAYS,
    apply_rules,
    is_in_grace_period,
)
from _lib.gmail_client import (  # noqa: E402
    get_service,
    iter_metadata,
    list_message_ids,
    trash_messages,
)
from _lib.db import connect  # noqa: E402


def _log_feedback(cur, email_id: str, rule_id: str, action: str) -> None:
    cur.execute(
        """
        INSERT INTO feedback (email_id, user_label, source)
        VALUES (%s, %s, %s)
        ON CONFLICT (email_id) DO UPDATE
            SET user_label = EXCLUDED.user_label,
                source = EXCLUDED.source,
                created_at = NOW()
        """,
        (email_id, "spam", f"auto_clean:{action}:{rule_id}"),
    )


def run_purge(dry_run: bool, days_window: int = 30) -> dict:
    service = get_service()
    now = datetime.now(timezone.utc)
    query = f"in:inbox newer_than:{days_window}d"
    ids = list_message_ids(service, query, max_results=5000)

    to_trash_spam: list[tuple[str, str, str]] = []
    to_trash_grace: list[tuple[str, str, str, int]] = []
    rule_hits: Counter = Counter()
    kept_protected = 0
    kept_unmatched = 0

    for meta in iter_metadata(service, ids):
        hit = apply_rules(meta.sender, meta.sender_domain, meta.subject)
        is_unread = "UNREAD" in meta.labels

        if hit is None:
            kept_unmatched += 1
            continue

        if hit.decision == "deletable":
            to_trash_spam.append((meta.id, hit.rule_id, meta.subject[:70]))
            rule_hits[f"DEL:{hit.rule_id}"] += 1
            continue

        # keep (transactional) — grace period check
        if meta.received_at is None:
            kept_protected += 1
            continue
        age_days = (now - meta.received_at).days
        if is_in_grace_period(meta.received_at, is_unread, now=now):
            kept_protected += 1
            continue
        if is_unread and age_days >= GRACE_PERIOD_DAYS:
            to_trash_grace.append((meta.id, hit.rule_id, meta.subject[:70], age_days))
            rule_hits[f"GRACE:{hit.rule_id}"] += 1
        else:
            kept_protected += 1

    result = {
        "scanned": len(ids),
        "deletable": len(to_trash_spam),
        "grace_expired": len(to_trash_grace),
        "protected_by_rule": kept_protected,
        "unmatched_passed_through": kept_unmatched,
        "rule_hits": dict(rule_hits.most_common()),
        "dry_run": dry_run,
        "sample_deletable": [
            {"rule": rid, "subject": subj}
            for _, rid, subj in to_trash_spam[:5]
        ],
        "sample_grace": [
            {"rule": rid, "age_days": age, "subject": subj}
            for _, rid, subj, age in to_trash_grace[:5]
        ],
    }

    if dry_run:
        return result

    all_to_trash = [t[0] for t in to_trash_spam] + [t[0] for t in to_trash_grace]
    if all_to_trash:
        trash_messages(service, all_to_trash)
        with connect() as conn, conn.cursor() as cur:
            for mid, rid, _ in to_trash_spam:
                _log_feedback(cur, mid, rid, "deletable")
            for mid, rid, _, _ in to_trash_grace:
                _log_feedback(cur, mid, rid, "grace_expired")
            conn.commit()
        result["trashed"] = len(all_to_trash)
    else:
        result["trashed"] = 0

    return result


def _authorized(headers: dict) -> bool:
    """Vercel Cron wstrzykuje Authorization: Bearer $CRON_SECRET."""
    expected = os.getenv("CRON_SECRET")
    if not expected:
        # Brak sekretu = endpoint publiczny (nie zalecane, tylko dev)
        return True
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    return auth == f"Bearer {expected}"


class handler(BaseHTTPRequestHandler):
    def _respond(self, status: int, body: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False, default=str).encode("utf-8"))

    def _run(self) -> None:
        headers = {k.lower(): v for k, v in self.headers.items()}
        if not _authorized(headers):
            self._respond(401, {"error": "unauthorized"})
            return
        qs = parse_qs(urlparse(self.path).query)
        dry = (qs.get("dry", ["0"])[0] == "1") or (os.getenv("DRY_RUN") == "1")
        try:
            result = run_purge(dry_run=dry)
            self._respond(200, result)
        except Exception as e:
            self._respond(500, {
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc(),
            })

    def do_GET(self) -> None:
        self._run()

    def do_POST(self) -> None:
        self._run()
