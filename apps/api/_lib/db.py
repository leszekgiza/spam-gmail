"""Neon Postgres connection helper.

Używa DATABASE_URL z Vercel env vars.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg


def get_dsn() -> str:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    return dsn


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(get_dsn(), autocommit=False) as conn:
        yield conn
