"""Codzienna obserwacja — pobiera maile z ostatnich 2 dni i zapisuje aktualny stan.

Dla każdego maila zapisuje gdzie LĄDOWAŁ (trash / inbox / archive / spam).
To są realne decyzje użytkownika = nowy training set.

Uruchamianie:
    python scripts/daily_learn.py [--days 2]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.gmail.auth import get_service  # noqa: E402
from packages.gmail.operations import iter_metadata, list_message_ids  # noqa: E402
from packages.shared.db import connect  # noqa: E402


def classify_state(labels: list[str]) -> str | None:
    """Zwraca finalny stan maila → user_label albo None jeśli niepewny."""
    if "TRASH" in labels:
        return "spam"
    if "SPAM" in labels:
        return "spam"
    if "INBOX" not in labels:
        return "keep"  # zarchiwizowany
    if "INBOX" in labels and "UNREAD" not in labels:
        return "keep"  # przeczytany, zostawiony
    return None  # świeży, jeszcze nie zdecydowany


def main(days: int = 2) -> None:
    service = get_service()
    query = f"newer_than:{days}d"
    print(f"Query: {query!r}")
    ids = list_message_ids(service, query, max_results=5000)
    print(f"Found {len(ids)} messages from last {days} days")

    inserted = updated = labeled = 0
    state_counts: Counter[str] = Counter()
    new_spam_domains: Counter[str] = Counter()
    new_keep_domains: Counter[str] = Counter()

    with connect() as conn, conn.cursor() as cur:
        for meta in iter_metadata(service, ids):
            cur.execute(
                """
                INSERT INTO raw_emails
                    (id, thread_id, sender, sender_domain, subject, snippet, labels, received_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET labels = EXCLUDED.labels
                RETURNING (xmax = 0) AS inserted
                """,
                (
                    meta.id, meta.thread_id, meta.sender, meta.sender_domain,
                    meta.subject, meta.snippet, meta.labels, meta.received_at,
                ),
            )
            was_new = cur.fetchone()[0]
            if was_new:
                inserted += 1
            else:
                updated += 1

            state = classify_state(meta.labels)
            if state:
                state_counts[state] += 1
                cur.execute(
                    """
                    INSERT INTO feedback (email_id, user_label, source)
                    VALUES (%s, %s, 'daily_observation')
                    ON CONFLICT (email_id) DO UPDATE
                        SET user_label = EXCLUDED.user_label,
                            source = 'daily_observation',
                            created_at = NOW()
                    """,
                    (meta.id, state),
                )
                labeled += 1
                if state == "spam":
                    new_spam_domains[meta.sender_domain] += 1
                else:
                    new_keep_domains[meta.sender_domain] += 1

        conn.commit()

    print(f"\nInserted new: {inserted}")
    print(f"Updated existing: {updated}")
    print(f"Labeled (with feedback): {labeled}")
    print(f"  spam: {state_counts['spam']}")
    print(f"  keep: {state_counts['keep']}")
    print(f"  uncertain (skipped): {len(ids) - labeled}")

    if new_spam_domains:
        print("\nTop nowo zaklasyfikowane jako SPAM (skasowane lub w SPAM):")
        for dom, n in new_spam_domains.most_common(15):
            print(f"  {dom:<40} {n:>4}")
    if new_keep_domains:
        print("\nTop nowo zaklasyfikowane jako KEEP (przeczytane/archiwum):")
        for dom, n in new_keep_domains.most_common(15):
            print(f"  {dom:<40} {n:>4}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=2)
    args = parser.parse_args()
    main(args.days)
