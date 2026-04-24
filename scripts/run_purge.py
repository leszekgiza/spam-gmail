"""Skrypt do uruchamiania purge z Windows Task Scheduler lub ręcznie.

Uruchamianie:
    python D:\Projekty\SPAMGmail\scripts\run_purge.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Załaduj env z .env.local
env_file = REPO / ".env.local"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k] = v.strip('"')

# Fallback DATABASE_URL
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (
        "postgresql://neondb_owner:npg_uihJAVm3LZ1T"
        "@ep-delicate-flower-alwttoit-pooler.c-3.eu-central-1.aws.neon.tech"
        "/neondb?sslmode=require"
    )

sys.path.insert(0, str(REPO / "apps" / "web" / "api"))

from cron.purge import run_purge  # noqa: E402

LOG_FILE = REPO / "logs" / "purge.log"


def main() -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        result = run_purge(dry_run=False, days_window=30)
        trashed = result.get("trashed", 0)
        summary = (
            f"[{now}] OK: scanned={result['scanned']} "
            f"trashed={trashed} "
            f"(rules={result['deletable_rules']} ml={result['deletable_ml']} "
            f"grace={result['grace_expired']}) "
            f"protected={result['protected_by_rule']} "
            f"ml_below={result['ml_below_threshold']}"
        )
        print(summary)
    except Exception as e:
        summary = f"[{now}] ERROR: {type(e).__name__}: {e}"
        print(summary, file=sys.stderr)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(summary + "\n")


if __name__ == "__main__":
    main()
