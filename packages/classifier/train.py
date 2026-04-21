"""Trening klasyfikatora na danych z Neon (raw_emails + feedback).

Uruchamianie:
    python -m packages.classifier.train
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import (
    classification_report, confusion_matrix, precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.classifier.features import build_features  # noqa: E402
from packages.classifier.model import build_pipeline  # noqa: E402
from packages.shared.db import connect  # noqa: E402

MODEL_VERSION = "v1_2026-04-15"
MODEL_DIR = REPO / "models"


def load_training_data() -> list[dict]:
    sql = """
        SELECT r.id, r.sender, r.sender_domain, r.subject, r.snippet,
               r.labels, r.received_at, f.user_label
          FROM raw_emails r
          JOIN feedback f ON r.id = f.email_id
    """
    with connect() as c, c.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def main() -> None:
    print(f"Loading training data from Neon...")
    rows = load_training_data()
    print(f"  {len(rows)} labeled examples")

    df = build_features(rows)
    y = df["user_label"].values
    print(f"  class distribution: keep={int((y=='keep').sum())}  spam={int((y=='spam').sum())}")

    X_train, X_test, y_train, y_test = train_test_split(
        df, y, test_size=0.2, stratify=y, random_state=42,
    )
    print(f"  train={len(X_train)}  test={len(X_test)}")

    results = {}
    for kind in ["logistic", "gbm"]:
        print(f"\n[{kind}] Training...")
        pipe = build_pipeline(kind)
        pipe.fit(X_train, y_train)

        pred = pipe.predict(X_test)
        print(classification_report(y_test, pred, digits=3))
        cm = confusion_matrix(y_test, pred, labels=["keep", "spam"])
        print(f"Confusion matrix (rows=actual, cols=pred) [keep, spam]:\n{cm}")

        p, r, f1, _ = precision_recall_fscore_support(
            y_test, pred, pos_label="spam", average="binary"
        )
        results[kind] = {"pipeline": pipe, "f1": f1, "precision": p, "recall": r}

    best = max(results.values(), key=lambda r: r["f1"])
    best_kind = [k for k, v in results.items() if v is best][0]
    print(f"\n>>> BEST: {best_kind} (F1={best['f1']:.3f}, precision={best['precision']:.3f}, recall={best['recall']:.3f})")

    MODEL_DIR.mkdir(exist_ok=True)
    out = MODEL_DIR / f"classifier_{MODEL_VERSION}.joblib"
    joblib.dump({
        "pipeline": best["pipeline"], "version": MODEL_VERSION,
        "kind": best_kind, "metrics": {
            "f1": best["f1"], "precision": best["precision"], "recall": best["recall"],
        },
    }, out)
    print(f"\nSaved to {out}")

    # Top uncertain — dobry zbiór do later LLM evaluation
    pipe = best["pipeline"]
    proba = pipe.predict_proba(X_test)
    classes = pipe.classes_
    spam_idx = int(np.where(classes == "spam")[0][0])
    spam_proba = proba[:, spam_idx]
    uncertain_mask = (spam_proba > 0.3) & (spam_proba < 0.7)
    print(f"\nUncertain examples (0.3 < P(spam) < 0.7): {uncertain_mask.sum()} / {len(X_test)}")


if __name__ == "__main__":
    main()
