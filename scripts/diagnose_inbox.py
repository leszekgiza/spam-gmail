"""Diagnostyka: dlaczego maile zostaja w inboxie? Odwzorowuje logike purge.py
na zywej skrzynce, ale NIC nie kasuje. Kategoryzuje decyzje per mail."""
from __future__ import annotations
import os, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
env_file = REPO / ".env.local"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k] = v.strip('"')

sys.path.insert(0, str(REPO))  # dla packages.classifier.model (joblib unpickle)
sys.path.insert(0, str(REPO / "apps" / "web" / "api"))
from _lib.rules import apply_rules, is_in_grace_period, GRACE_PERIOD_DAYS  # noqa
from _lib.gmail_client import get_service, iter_metadata, list_message_ids  # noqa
from _lib.scorer import score_email  # noqa

ML_SPAM_THRESHOLD = 0.80

svc = get_service()
now = datetime.now(timezone.utc)
query = "in:inbox newer_than:30d"
ids = list_message_ids(svc, query, max_results=5000)
print(f"Inbox (newer_than:30d): {len(ids)} maili\n")

# kategorie decyzji
cat = Counter()
keep_rule_hits = Counter()
kept_ml_below = []   # (p, sender, subject)
kept_unmatched = []  # brak reguly, brak modelu
would_delete = []    # rule deletable lub ML>=threshold
keep_by_sender = defaultdict(list)

for meta in iter_metadata(svc, ids):
    hit = apply_rules(meta.sender, meta.sender_domain, meta.subject)
    if hit is not None:
        if hit.decision == "keep":
            cat["KEEP_rule"] += 1
            keep_rule_hits[hit.rule_id] += 1
            keep_by_sender[hit.rule_id].append((meta.sender[:40], (meta.subject or "")[:55]))
        else:
            cat["DELETE_rule"] += 1
            would_delete.append((meta.sender[:40], (meta.subject or "")[:55], "rule:" + hit.rule_id))
        continue
    res = score_email(meta.sender_domain, meta.subject, meta.snippet, meta.received_at)
    if res is None:
        cat["KEPT_no_model"] += 1
        kept_unmatched.append((meta.sender[:40], (meta.subject or "")[:55]))
        continue
    p, ver = res
    if p >= ML_SPAM_THRESHOLD:
        cat["DELETE_ml"] += 1
        would_delete.append((meta.sender[:40], (meta.subject or "")[:55], f"ml:{p:.2f}"))
    else:
        cat["KEPT_ml_below"] += 1
        kept_ml_below.append((p, meta.sender[:40], (meta.subject or "")[:55]))

print("=== PODSUMOWANIE DECYZJI ===")
for k, v in cat.most_common():
    print(f"  {k:18s} {v}")

print("\n=== KEEP przez reguly (wg rule_id) ===")
for rid, n in keep_rule_hits.most_common():
    print(f"  {rid:32s} {n}")

print("\n=== KEEP rule: przyklady (top reguly) ===")
for rid, _ in keep_rule_hits.most_common(8):
    print(f"\n  [{rid}]")
    for s, subj in keep_by_sender[rid][:6]:
        print(f"      {s:42s} | {subj}")

print("\n=== KEPT ml<0.85: top 40 wg p (najblizej progu = najbardziej podejrzane) ===")
for p, s, subj in sorted(kept_ml_below, reverse=True)[:40]:
    print(f"  p={p:.2f}  {s:42s} | {subj}")

print(f"\n=== KEPT_no_model: {len(kept_unmatched)} (przyklady) ===")
for s, subj in kept_unmatched[:20]:
    print(f"  {s:42s} | {subj}")

print(f"\n=== WOULD DELETE teraz (gdyby cron puscic): {len(would_delete)} ===")
for s, subj, why in would_delete:
    print(f"  [{why:32s}] {s:42s} | {subj}")
