"""Wykrywa nowe decyzje użytkownika porównując aktualny stan Gmaila z DB.

Strategia:
1. Pobierz CO JEST TERAZ w TRASH (newer_than:30d po received_at — limit kosztu)
2. Porównaj z feedback: które ID nie mają jeszcze user_label='spam' z source='daily_observation'?
3. Dla nowych → zapisz jako świeży spam_observation
4. Analogicznie dla INBOX (przeczytane bez UNREAD = świadomy keep)

Uruchamianie: python scripts/detect_changes.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.gmail.auth import get_service  # noqa: E402
from packages.gmail.operations import iter_metadata, list_message_ids  # noqa: E402
from packages.shared.db import connect  # noqa: E402


def main() -> None:
    service = get_service()

    print("=== Krok 1: aktualnie w TRASH (ostatnie 30 dni wedle received) ===")
    trash_ids = list_message_ids(service, "in:trash newer_than:30d", max_results=10000)
    print(f"Gmail TRASH: {len(trash_ids)} maili")

    print("\n=== Krok 2: aktualnie w INBOX przeczytane (świadomy keep) ===")
    read_inbox_ids = list_message_ids(
        service, "in:inbox -in:unread newer_than:30d", max_results=10000,
    )
    print(f"INBOX przeczytane: {len(read_inbox_ids)} maili")

    new_spam = []
    new_keep = []
    spam_dom: Counter[str] = Counter()
    keep_dom: Counter[str] = Counter()

    with connect() as conn, conn.cursor() as cur:
        # Sprawdź które ID w trash NIE mają jeszcze feedback='spam'
        if trash_ids:
            cur.execute(
                """
                SELECT id FROM raw_emails
                WHERE id = ANY(%s)
                  AND id NOT IN (SELECT email_id FROM feedback WHERE user_label='spam')
                """,
                (trash_ids,),
            )
            existing_unlabeled_spam = {r[0] for r in cur.fetchall()}

            # I te które nie ma jeszcze w raw_emails wcale
            cur.execute("SELECT id FROM raw_emails WHERE id = ANY(%s)", (trash_ids,))
            in_db = {r[0] for r in cur.fetchall()}
            missing_from_db = set(trash_ids) - in_db

            new_spam_ids = list(existing_unlabeled_spam | missing_from_db)
            print(f"\nNowych SPAM observations: {len(new_spam_ids)}")
            print(f"  - już w DB ale bez spam-label: {len(existing_unlabeled_spam)}")
            print(f"  - nieznanych w DB:             {len(missing_from_db)}")

            for meta in iter_metadata(service, new_spam_ids):
                cur.execute(
                    """
                    INSERT INTO raw_emails
                        (id, thread_id, sender, sender_domain, subject, snippet, labels, received_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET labels = EXCLUDED.labels
                    """,
                    (
                        meta.id, meta.thread_id, meta.sender, meta.sender_domain,
                        meta.subject, meta.snippet, meta.labels, meta.received_at,
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO feedback (email_id, user_label, source)
                    VALUES (%s, 'spam', 'daily_observation')
                    ON CONFLICT (email_id) DO UPDATE
                        SET user_label='spam', source='daily_observation', created_at=NOW()
                    """,
                    (meta.id,),
                )
                spam_dom[meta.sender_domain] += 1
                new_spam.append((meta.received_at, meta.sender_domain, meta.subject))

        # KEEP: przeczytane w INBOX, których nie ma jeszcze w feedback='keep'
        if read_inbox_ids:
            cur.execute(
                """
                SELECT id FROM raw_emails
                WHERE id = ANY(%s)
                  AND id NOT IN (SELECT email_id FROM feedback WHERE user_label='keep')
                """,
                (read_inbox_ids,),
            )
            existing_unlabeled_keep = {r[0] for r in cur.fetchall()}
            cur.execute("SELECT id FROM raw_emails WHERE id = ANY(%s)", (read_inbox_ids,))
            in_db_k = {r[0] for r in cur.fetchall()}
            missing_keep = set(read_inbox_ids) - in_db_k
            new_keep_ids = list(existing_unlabeled_keep | missing_keep)
            print(f"\nNowych KEEP observations: {len(new_keep_ids)}")

            for meta in iter_metadata(service, new_keep_ids):
                cur.execute(
                    """
                    INSERT INTO raw_emails
                        (id, thread_id, sender, sender_domain, subject, snippet, labels, received_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET labels = EXCLUDED.labels
                    """,
                    (
                        meta.id, meta.thread_id, meta.sender, meta.sender_domain,
                        meta.subject, meta.snippet, meta.labels, meta.received_at,
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO feedback (email_id, user_label, source)
                    VALUES (%s, 'keep', 'daily_observation')
                    ON CONFLICT (email_id) DO UPDATE
                        SET user_label='keep', source='daily_observation', created_at=NOW()
                    """,
                    (meta.id,),
                )
                keep_dom[meta.sender_domain] += 1
                new_keep.append((meta.received_at, meta.sender_domain, meta.subject))

        conn.commit()

    print("\n" + "=" * 70)
    print(f"PODSUMOWANIE: +{len(new_spam)} spam, +{len(new_keep)} keep observations")

    if spam_dom:
        print(f"\nTop nadawców NOWO oznaczonych jako spam:")
        for d, n in spam_dom.most_common(10):
            print(f"  {d:<40} {n:>4}")
    if new_spam:
        print(f"\nPróbka 10 świeżo skasowanych:")
        for dt, dom, subj in sorted(new_spam, reverse=True)[:10]:
            print(f"  {dt.date() if dt else 'NULL'}  [{dom[:25]:<25}] {subj[:60] if subj else ''}")

    if keep_dom:
        print(f"\nTop nadawców NOWO oznaczonych jako keep:")
        for d, n in keep_dom.most_common(10):
            print(f"  {d:<40} {n:>4}")


if __name__ == "__main__":
    main()
