"""SQLite connection helper — SHIM: pending naru#6.

Every repo-side DB access goes through connect(): a context manager that
guarantees the connection is closed, sets a busy_timeout so lock contention
waits instead of erroring/hanging, and enables WAL so readers never block on a
writer. This is the minimal fix for the Session-2A "database is locked" hangs
(root cause + naru gap write-up in docs/naru_gaps.md, naru#6): connections that
were never context-managed and a default busy_timeout of 0.

WAL and busy_timeout are the load-bearing settings. WAL is a persistent database
property (set once, harmless to repeat); busy_timeout is per-connection.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

BUSY_TIMEOUT_MS = 30_000


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with WAL + busy_timeout, guaranteed to close."""
    conn = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000)
    try:
        conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        yield conn
    finally:
        conn.close()
