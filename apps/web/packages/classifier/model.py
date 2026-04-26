"""Stub module for unpickling sklearn model.

The model was trained with `analyzer=_identity_analyzer` from
`packages.classifier.model`. At runtime, joblib needs this exact path
to deserialize the TfidfVectorizer's analyzer. This stub provides only
the function needed for unpickling.

Do NOT use this for training — see canonical packages/classifier/model.py.
"""
from __future__ import annotations


def _identity_analyzer(x: str) -> list[str]:
    """Module-level fn (picklable) — traktuje domain jako jeden token."""
    return [x] if x else []
