"""Statystyki kasowania — czyta DATABASE_URL z .env.local."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
env_file = REPO / ".env.local"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k] = v.strip('"')

import psycopg  # noqa: E402

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw_emails;")
        print(f"raw_emails total:        {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM feedback;")
        print(f"feedback total:          {cur.fetchone()[0]}")

        cur.execute("SELECT source, COUNT(*) FROM feedback GROUP BY source ORDER BY 2 DESC;")
        print("\n=== feedback by source ===")
        for src, n in cur.fetchall():
            print(f"  {src:20s} {n}")

        cur.execute("""
            SELECT DATE(created_at) AS d, COUNT(*)
            FROM feedback
            WHERE source IN ('auto_clean','user_restore')
              AND created_at > NOW() - INTERVAL '14 days'
            GROUP BY d ORDER BY d DESC;
        """)
        print("\n=== daily auto_clean+restore (last 14 days) ===")
        for d, n in cur.fetchall():
            print(f"  {d}  {n}")

        cur.execute("""
            SELECT DATE(created_at) AS d, source, COUNT(*)
            FROM feedback
            WHERE created_at > NOW() - INTERVAL '14 days'
            GROUP BY d, source ORDER BY d DESC, source;
        """)
        print("\n=== daily breakdown by source (last 14d) ===")
        for d, src, n in cur.fetchall():
            print(f"  {d}  {src:20s} {n}")
