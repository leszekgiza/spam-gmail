"""Co dzisiaj cron wyrzucił + szczegóły konkretnych nadawców."""
from __future__ import annotations
import os, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
env_file = REPO / ".env.local"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k] = v.strip('"')

import psycopg

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        print("=== WSZYSTKIE auto_clean z dzisiaj (2026-05-12) ===\n")
        cur.execute("""
            SELECT f.source, r.sender, r.subject, r.received_at
            FROM feedback f
            JOIN raw_emails r ON r.id = f.email_id
            WHERE DATE(f.created_at) = '2026-05-12'
              AND f.source LIKE 'auto_clean%'
            ORDER BY f.created_at;
        """)
        rows = cur.fetchall()
        print(f"Total: {len(rows)}\n")
        for src, sender, subj, recv in rows:
            print(f"[{src[:50]}]")
            print(f"  From: {sender}")
            print(f"  Subj: {(subj or '')[:80]}")
            print(f"  Recv: {recv}\n")

        print("\n=== Szukanie konkretnych nadawców (Skrzypkowski/Unconference/Warsaw.AI) ===\n")
        cur.execute("""
            SELECT f.source, f.created_at, r.sender, r.subject
            FROM feedback f
            JOIN raw_emails r ON r.id = f.email_id
            WHERE (LOWER(r.sender) LIKE '%skrzypkowski%'
                OR LOWER(r.subject) LIKE '%unconference%'
                OR LOWER(r.subject) LIKE '%warsaw.ai%'
                OR LOWER(r.subject) LIKE '%warsawai%'
                OR LOWER(r.sender) LIKE '%warsaw.ai%')
            ORDER BY f.created_at DESC LIMIT 30;
        """)
        for src, created, sender, subj in cur.fetchall():
            print(f"[{created}] {src}")
            print(f"  From: {sender}")
            print(f"  Subj: {(subj or '')[:100]}\n")
