"""Pipeline klasyfikatora — ColumnTransformer z TF-IDF + kategoryczne + numeryczne."""
from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import (
    CATEGORICAL_COLS, KEYWORD_COLS, NUMERIC_COLS,
    TEXT_COL_SNIPPET, TEXT_COL_SUBJECT,
)


def _identity_analyzer(x: str) -> list[str]:
    """Module-level fn (picklable) — traktuje domain jako jeden token."""
    return [x] if x else []


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("subject_tfidf", TfidfVectorizer(
                lowercase=True, ngram_range=(1, 2), min_df=2, max_df=0.9,
                max_features=5000, sublinear_tf=True,
            ), TEXT_COL_SUBJECT),
            ("snippet_tfidf", TfidfVectorizer(
                lowercase=True, ngram_range=(1, 1), min_df=3, max_df=0.9,
                max_features=5000, sublinear_tf=True,
            ), TEXT_COL_SNIPPET),
            ("domain", TfidfVectorizer(
                analyzer=_identity_analyzer, lowercase=False, min_df=1,
            ), CATEGORICAL_COLS[0]),
            ("numeric", StandardScaler(with_mean=False), NUMERIC_COLS + KEYWORD_COLS),
        ],
        remainder="drop",
        sparse_threshold=0.5,
    )


def build_pipeline(kind: str = "logistic") -> Pipeline:
    pre = build_preprocessor()
    if kind == "logistic":
        clf = LogisticRegression(
            max_iter=2000, C=1.0, class_weight="balanced", solver="liblinear",
        )
    elif kind == "gbm":
        clf = GradientBoostingClassifier(
            n_estimators=300, max_depth=3, learning_rate=0.05, random_state=42,
        )
    else:
        raise ValueError(f"Unknown kind: {kind}")
    return Pipeline([("pre", pre), ("clf", clf)])
