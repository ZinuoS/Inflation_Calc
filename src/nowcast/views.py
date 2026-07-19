"""Derived vintage views over the observations table.

Read-only SQL views, deterministic and offline (rule 4). Created after the
alfred_vintages load.

- first_release_mom  ← THE CANONICAL MoM TARGET (research plan D2/D3).
  Within-vintage MoM: for reference month t, both level_t and level_{t-1} are read
  from the SINGLE vintage published at t's first release. This is the only
  leakage- and re-referencing-safe way to form a first-release MoM. See the long
  note on _FIRST_RELEASE_MOM below.

- first_release (levels) ← DIAGNOSTIC ONLY. The earliest-vintage LEVEL per
  (series, reference_period). Correct as a level, but *** differencing these levels
  across adjacent months fabricates fake MoM *** whenever a base re-referencing
  (e.g. PCEPILFE at the BEA comprehensive update: 2023-07 first-released 128.579 on
  the old base, its neighbours on the new base) or a February seasonal-factor
  restatement lands between the two releases: t and t-1 would then sit on different
  bases. Use first_release_mom for MoM; use this only to inspect first-print levels.
  It remains the source of first-release *vintage dates* for reference-period
  reassignment in timebase.py.

- latest_value ← the most-recent-vintage value per (series, reference_period): the
  fully-revised number, tracked separately, never a backtest target.

All restrict to naru-active rows (_superseded_by_run_id IS NULL). Because the
observations key includes observed_asof_vintage, distinct vintages never supersede
one another, so every vintage row is active -- the filter is belt-and-suspenders.
"""

from __future__ import annotations

from pathlib import Path

from nowcast import db

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


_FIRST_RELEASE_MOM = """
CREATE VIEW IF NOT EXISTS first_release_mom AS
SELECT fr.series_id,
       fr.mapping_series_id,
       fr.reference_period,
       fr.first_release_vintage        AS vintage,
       fr.first_release_value          AS level_t,
       prev.value                      AS level_prev,
       (fr.first_release_value / prev.value) - 1.0  AS mom
FROM first_release fr
JOIN observations prev
  ON prev.series_id = fr.series_id
 -- t-1's value AS OBSERVED IN THE SAME VINTAGE t was first released in: the row
 -- whose inclusive window [observed_asof_vintage, vintage_end] contains t's
 -- first-release vintage. Reading t-1 from that vintage (not from t-1's own first
 -- release) is what makes the ratio survive a base re-referencing or a seasonal
 -- restatement landing between the two releases.
 AND prev.reference_period = date(fr.reference_period, '-1 month')
 AND prev.observed_asof_vintage <= fr.first_release_vintage
 AND prev.vintage_end          >= fr.first_release_vintage
 AND prev._superseded_by_run_id IS NULL;
"""


def create_views(db_path: str | Path) -> None:
    with db.connect(db_path) as conn:
        conn.executescript(_INDEX)
        conn.executescript(_FIRST_RELEASE)
        conn.executescript(_LATEST_VALUE)
        conn.executescript(_FIRST_RELEASE_MOM)
        conn.commit()
