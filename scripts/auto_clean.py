"""Codzienne auto-czyszczenie skrzynki (uruchamiane o 6:00 rano).

Stosuje DWIE reguły z packages/classifier/rules.py:
  1. Hard-rules DELETABLE (temu, otomoto, beehiiv, newsletter.allegro, ...)
     → natychmiast do kosza.
  2. Hard-rules KEEP (bank, vercel security/ops, allegropay, meta ads billing, ...)
     + 7-dniowy grace period: jeśli UNREAD > 7 dni → do kosza
     (user i tak nie otworzył, nie było pilne).

Wszystko inne (model ML — jeszcze nie zadecydował) zostaje w INBOX, żeby user
sam pokazał swoją decyzję — to jest training set dla kolejnych iteracji.

Każda akcja loguje się do tabeli `feedback` z source='auto_clean_rule' + rule_id,
żeby można było audytować i odzyskać (użycie mcp__claude_ai_Gmail__ — mail w TRASH
nadal istnieje 30 dni).

Uruchomienie:
    python scripts/auto_clean.py            # live
    python scripts/auto_clean.py --dry-run  # pokaż co by zrobił
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from packages.classifier.rules import (  # noqa: E402
    GRACE_PERIOD_DAYS,
    apply_rules,
    is_in_grace_period,
)
from packages.gmail.auth import get_service  # noqa: E402
from packages.gmail.operations import (  # noqa: E402
    iter_metadata,
    list_message_ids,
    trash_messages,
)
from packages.shared.db import connect  # noqa: E402


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


def main(dry_run: bool = False, days_window: int = 30) -> None:
    service = get_service()
    now = datetime.now(timezone.utc)

    query = f"in:inbox newer_than:{days_window}d"
    print(f"[auto_clean] query={query!r} dry_run={dry_run}")
    ids = list_message_ids(service, query, max_results=5000)
    print(f"[auto_clean] scanned {len(ids)} messages in INBOX")

    to_trash_spam: list[tuple[str, str, str]] = []       # (id, rule, subject)
    to_trash_grace: list[tuple[str, str, str, int]] = []  # (id, rule, subject, age)
    rule_hits: Counter[str] = Counter()
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

        # decision == "keep" (transactional) — grace period check
        if meta.received_at is None:
            kept_protected += 1
            continue
        age_days = (now - meta.received_at).days
        if is_in_grace_period(meta.received_at, is_unread, now=now):
            kept_protected += 1
            continue
        # poza grace period: jeśli nadal UNREAD → do kosza, inaczej zostaw (user czytał)
        if is_unread and age_days >= GRACE_PERIOD_DAYS:
            to_trash_grace.append((meta.id, hit.rule_id, meta.subject[:70], age_days))
            rule_hits[f"GRACE:{hit.rule_id}"] += 1
        else:
            kept_protected += 1

    print(f"\n[auto_clean] plan:")
    print(f"  DELETABLE (hard spam):        {len(to_trash_spam)}")
    print(f"  GRACE EXPIRED (>{GRACE_PERIOD_DAYS}d unread): {len(to_trash_grace)}")
    print(f"  KEEP (rule-protected):        {kept_protected}")
    print(f"  UNMATCHED (zostawione modelowi): {kept_unmatched}")

    if rule_hits:
        print("\n[auto_clean] hits by rule:")
        for rid, n in rule_hits.most_common():
            print(f"  {rid:<50} {n:>5}")

    if to_trash_spam:
        print("\n[auto_clean] sample DELETABLE:")
        for _, rid, subj in to_trash_spam[:5]:
            print(f"  [{rid}] {subj}")
    if to_trash_grace:
        print(f"\n[auto_clean] sample GRACE EXPIRED (unread >{GRACE_PERIOD_DAYS}d):")
        for _, rid, subj, age in to_trash_grace[:5]:
            print(f"  [{rid}] {age}d  {subj}")

    if dry_run:
        print("\n[auto_clean] --dry-run: nic nie zmieniono.")
        return

    all_to_trash = [t[0] for t in to_trash_spam] + [t[0] for t in to_trash_grace]
    if not all_to_trash:
        print("\n[auto_clean] nic do usunięcia.")
        return

    trash_messages(service, all_to_trash)

    with connect() as conn, conn.cursor() as cur:
        for mid, rid, _ in to_trash_spam:
            _log_feedback(cur, mid, rid, "deletable")
        for mid, rid, _, _ in to_trash_grace:
            _log_feedback(cur, mid, rid, "grace_expired")
        conn.commit()

    print(f"\n[auto_clean] ✓ przeniesiono do kosza: {len(all_to_trash)} "
          f"({len(to_trash_spam)} spam + {len(to_trash_grace)} grace)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--days", type=int, default=30, help="okno skanowania INBOX")
    args = parser.parse_args()
    main(dry_run=args.dry_run, days_window=args.days)
