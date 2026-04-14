"""Jednorazowy bootstrap: pobierz 12 mies. historii skrzynki → Neon + auto-labeling training set.

Reguły auto-labelingu (PRD faza 0):
- w koszu / w spamie        → feedback.user_label='spam'  source='bootstrap_trash'
- przeczytane + INBOX >30d  → feedback.user_label='keep'  source='bootstrap_inbox_old'
- przeczytane + zarchiwizowane → feedback.user_label='keep' source='bootstrap_archived'
- nieprzeczytane >14d + nieskasowane → pomijane (niska waga)

Uruchomienie (lokalnie, z .secrets/credentials.json):
    python scripts/bootstrap_history.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.gmail.auth import get_service  # noqa: E402
from packages.gmail.operations import iter_metadata, list_message_ids  # noqa: E402
from packages.shared.db import connect  # noqa: E402

QUERIES = {
    "bootstrap_trash": "in:trash newer_than:365d",
    "bootstrap_spam": "in:spam newer_than:365d",
    "bootstrap_archived": "-in:inbox -in:trash -in:spam newer_than:365d",
    "bootstrap_inbox": "in:inbox newer_than:365d",
}

LABEL_MAP = {
    "bootstrap_trash": "spam",
    "bootstrap_spam": "spam",
    "bootstrap_archived": "keep",
    "bootstrap_inbox": None,  # decide per-message based on age + unread
}


def classify_inbox(meta, now: datetime) -> str | None:
    """Zwraca 'keep' / None wedle reguł faz 0 dla skrzynki INBOX."""
    if meta.received_at is None:
        return None
    age_days = (now - meta.received_at).days
    is_unread = "UNREAD" in meta.labels
    if not is_unread and age_days > 30:
        return "keep"
    if is_unread and age_days > 14:
        return None
    return None


def main(limit_per_query: int = 2000) -> None:
    service = get_service()
    now = datetime.now(timezone.utc)

    with connect() as conn, conn.cursor() as cur:
        total_inserted = 0
        total_feedback = 0
        for source, query in QUERIES.items():
            print(f"[{source}] query={query!r}")
            ids = list_message_ids(service, query, max_results=limit_per_query)
            print(f"  found {len(ids)} message ids")

            for meta in iter_metadata(service, ids):
                cur.execute(
                    """
                    INSERT INTO raw_emails
                        (id, thread_id, sender, sender_domain, subject, snippet, labels, received_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        meta.id, meta.thread_id, meta.sender, meta.sender_domain,
                        meta.subject, meta.snippet, meta.labels, meta.received_at,
                    ),
                )
                total_inserted += cur.rowcount

                label = LABEL_MAP[source]
                if label is None and source == "bootstrap_inbox":
                    label = classify_inbox(meta, now)
                if label is not None:
                    cur.execute(
                        """
                        INSERT INTO feedback (email_id, user_label, source)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (email_id) DO NOTHING
                        """,
                        (meta.id, label, source),
                    )
                    total_feedback += cur.rowcount

            conn.commit()
            print(f"  committed. total_emails={total_inserted} total_feedback={total_feedback}")

    print(f"\nDone. inserted={total_inserted} feedback_rows={total_feedback}")


if __name__ == "__main__":
    main()
