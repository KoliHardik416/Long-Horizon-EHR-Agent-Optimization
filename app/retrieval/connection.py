"""PostgreSQL connection helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row


POOL_MIN_SIZE = int(os.environ.get("PGPOOL_MIN_SIZE", "2"))
POOL_MAX_SIZE = int(os.environ.get("PGPOOL_MAX_SIZE", "10"))


_POOLS: dict[str, ConnectionPool] = {}


def _pool(conninfo: str) -> ConnectionPool:
    """Create one shared pool per connection string."""
    if conninfo not in _POOLS:
        pool = ConnectionPool(
            conninfo=conninfo,
            min_size=POOL_MIN_SIZE,
            max_size=POOL_MAX_SIZE,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        pool.open(wait=True)
        _POOLS[conninfo] = pool
    return _POOLS[conninfo]


@contextmanager
def connect(conninfo: str | None = None) -> Iterator[psycopg.Connection]:
    """Borrow a connection from a shared pool using DATABASE_URL or PG* vars."""
    resolved = conninfo or os.environ.get("DATABASE_URL") or ""
    with _pool(resolved).connection() as conn:
        yield conn


def close_pools() -> None:
    """Close all cached pools, useful during application shutdown and tests."""
    for pool in _POOLS.values():
        pool.close()
    _POOLS.clear()

