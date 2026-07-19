"""Offline tests for the vintage views (first_release / latest_value).

Builds a tiny observations table shaped like naru's output (row_id PK +
_superseded_by_run_id) and asserts first_release picks the earliest vintage per
(series, reference_period) and latest_value the most recent -- the load-bearing
semantics for the backtest target and PCE reference reassignment.
"""

import sqlite3
from pathlib import Path

from nowcast.views import create_views


def _make_db(tmp_path: Path) -> Path:
    db = tmp_path / "obs.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE observations (
            row_id INTEGER PRIMARY KEY, series_id TEXT, mapping_series_id TEXT,
            reference_period TEXT, observed_asof_vintage TEXT, vintage_end TEXT,
            value REAL, _run_id INTEGER, _verification TEXT, _superseded_by_run_id INTEGER
        )"""
    )
    rows = [
        # X / 2020-01: three vintages -> first 100.0@02-13, latest 102.0@2022
        ("X", "2020-01-01", "2020-02-13", 100.0, None),
        ("X", "2020-01-01", "2021-02-10", 101.0, None),
        ("X", "2020-01-01", "2022-02-09", 102.0, None),
        # X / 2020-02: single vintage
        ("X", "2020-02-01", "2020-03-11", 200.0, None),
        # Y / 2020-01: two vintages
        ("Y", "2020-01-01", "2020-02-27", 50.0, None),
        ("Y", "2020-01-01", "2021-03-01", 55.0, None),
    ]
    for i, (s, ref, vin, val, sup) in enumerate(rows, start=1):
        conn.execute(
            "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?)",
            (i, s, s, ref, vin, "9999-12-31", val, 1, "TO_VERIFY", sup),
        )
    conn.commit()
    conn.close()
    return db


def test_first_release_picks_earliest_vintage(tmp_path):
    db = _make_db(tmp_path)
    create_views(db)
    conn = sqlite3.connect(db)
    got = dict(
        conn.execute(
            "SELECT series_id || '/' || reference_period, first_release_value FROM first_release"
        ).fetchall()
    )
    assert got["X/2020-01-01"] == 100.0   # earliest vintage 2020-02-13
    assert got["X/2020-02-01"] == 200.0
    assert got["Y/2020-01-01"] == 50.0    # earliest vintage 2020-02-27
    # one first-release row per (series, reference_period)
    assert conn.execute("SELECT count(*) FROM first_release").fetchone()[0] == 3


def test_latest_value_picks_most_recent_vintage(tmp_path):
    db = _make_db(tmp_path)
    create_views(db)
    conn = sqlite3.connect(db)
    got = dict(
        conn.execute(
            "SELECT series_id || '/' || reference_period, latest_value FROM latest_value"
        ).fetchall()
    )
    assert got["X/2020-01-01"] == 102.0
    assert got["Y/2020-01-01"] == 55.0


def test_first_release_vintage_recorded(tmp_path):
    db = _make_db(tmp_path)
    create_views(db)
    conn = sqlite3.connect(db)
    vin = conn.execute(
        "SELECT first_release_vintage FROM first_release WHERE series_id='X' AND reference_period='2020-01-01'"
    ).fetchone()[0]
    assert vin == "2020-02-13"
