"""Derived vintage views over the observations table.

Read-only SQL views, deterministic and offline (rule 4). Created after the
alfred_vintages load. Two views:

- first_release: the earliest-vintage value per (series, reference_period) -- the
  value the market actually traded on release day (research plan D3). This is the
  backtest target and the authoritative source for reassigning PCE reference
  periods in the release_calendar (timebase.py, Task 3).
- latest_value: the most-recent-vintage value per (series, reference_period) --
  the fully-revised number, tracked separately, never a backtest target.

Both restrict to naru-active rows (_superseded_by_run_id IS NULL). Because the
observations key includes observed_asof_vintage, distinct vintages never supersede
one another, so every vintage row is active -- the filter is belt-and-suspenders.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# naru creates final tables with only a row_id PK, so the vintage views'
# correlated MIN/MAX-per-(series, reference_period) subqueries would scan the
# whole 48k-row observations table per row (O(n^2)). This index -- a read-only
# optimization that touches no data, so it doesn't violate "only naru writes
# rows" -- makes those subqueries index lookups.
_INDEX = """
CREATE INDEX IF NOT EXISTS ix_observations_series_ref_vintage
    ON observations (series_id, reference_period, observed_asof_vintage);
"""

_FIRST_RELEASE = """
CREATE VIEW IF NOT EXISTS first_release AS
SELECT o.series_id,
       o.mapping_series_id,
       o.reference_period,
       o.value                 AS first_release_value,
       o.observed_asof_vintage AS first_release_vintage
FROM observations o
WHERE o._superseded_by_run_id IS NULL
  AND o.observed_asof_vintage = (
        SELECT MIN(o2.observed_asof_vintage)
        FROM observations o2
        WHERE o2.series_id = o.series_id
          AND o2.reference_period = o.reference_period
          AND o2._superseded_by_run_id IS NULL
  );
"""

_LATEST_VALUE = """
CREATE VIEW IF NOT EXISTS latest_value AS
SELECT o.series_id,
       o.mapping_series_id,
       o.reference_period,
       o.value                 AS latest_value,
       o.observed_asof_vintage AS latest_vintage
FROM observations o
WHERE o._superseded_by_run_id IS NULL
  AND o.observed_asof_vintage = (
        SELECT MAX(o2.observed_asof_vintage)
        FROM observations o2
        WHERE o2.series_id = o.series_id
          AND o2.reference_period = o.reference_period
          AND o2._superseded_by_run_id IS NULL
  );
"""


def create_views(db_path: Path) -> None:
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.executescript(_INDEX)
        conn.executescript(_FIRST_RELEASE)
        conn.executescript(_LATEST_VALUE)
        conn.commit()
    finally:
        conn.close()
