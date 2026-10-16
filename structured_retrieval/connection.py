"""PostgreSQL connection helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


@contextmanager
def connect(conninfo: str | None = None) -> Iterator[psycopg.Connection]:
    """Open a PostgreSQL connection using DATABASE_URL or PG* variables."""
    resolved = conninfo or os.environ.get("DATABASE_URL")
    if resolved:
        with psycopg.connect(resolved, row_factory=dict_row) as conn:
            yield conn
    else:
        with psycopg.connect(row_factory=dict_row) as conn:
            yield conn

