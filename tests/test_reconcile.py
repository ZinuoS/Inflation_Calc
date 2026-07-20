"""Tests for alignment.py + reconcile.py (Session 2B, Task 2-3).

Offline unit tests for the deterministic pieces (BLS monthly averaging, OLS), plus a
real-DB regression test that locks in the Gate-2 findings: gasoline→energy stable,
ZORI→rent unstable + optimism-flagged (the pre-registered H2 result), monitors not
regressed. The real-DB test skips if nowcast.sqlite is absent.
"""

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from nowcast import alignment, reconcile

DB = Path(__file__).parent.parent / "data" / "db" / "nowcast.sqlite"
MAPPING = Path(__file__).parent.parent / "mapping" / "mapping.yaml"


# ---------- alignment (offline synthetic) ----------

def _proxy_db(tmp_path: Path, rows: list[tuple]) -> Path:
    db = tmp_path / "p.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE proxy_observations (source TEXT, series_key TEXT, frequency TEXT, "
        "period TEXT, value REAL, vintage_status TEXT, observed_date TEXT, _superseded_by_run_id INTEGER)"
    )
    conn.executemany(
        "INSERT INTO proxy_observations (source,series_key,frequency,period,value,_superseded_by_run_id) "
        "VALUES (?,?,?,?,?,NULL)", rows
    )
    conn.commit()
    conn.close()
    return db


def test_weekly_aligns_to_monthly_mean(tmp_path):
    # two weeks in Jan (mean 10), one week in Feb (20)
    db = _proxy_db(tmp_path, [
        ("s", "US", "weekly", "2024-01-05", 8.0),
        ("s", "US", "weekly", "2024-01-19", 12.0),
        ("s", "US", "weekly", "2024-02-02", 20.0),
    ])
    levels = alignment.monthly_levels(db, "s", "US")
    assert levels == {"2024-01-01": 10.0, "2024-02-01": 20.0}
    mom = alignment.monthly_mom(db, "s", "US")
    assert mom == {"2024-02-01": pytest.approx(1.0)}  # 20/10 - 1


def test_monthly_is_identity(tmp_path):
    db = _proxy_db(tmp_path, [
        ("z", "US", "monthly", "2024-01-01", 100.0),
        ("z", "US", "monthly", "2024-02-01", 101.0),
    ])
    assert alignment.monthly_levels(db, "z", "US") == {"2024-01-01": 100.0, "2024-02-01": 101.0}
    assert alignment.monthly_mom(db, "z", "US")["2024-02-01"] == pytest.approx(0.01)


# ---------- OLS ----------

def test_ols_recovers_known_slope():
    x = np.linspace(0, 1, 40)
    y = 2.0 * x + 0.5  # perfect line
    beta, r2 = reconcile._ols(x, y)
    assert beta == pytest.approx(2.0, abs=1e-9)
    assert r2 == pytest.approx(1.0, abs=1e-9)


# ---------- real-DB Gate-2 regression ----------

@pytest.mark.skipif(not DB.exists(), reason="nowcast.sqlite not built")
def test_gate2_findings():
    results = {r.label: r for r in reconcile.run(str(DB), reconcile.build_pairs(str(MAPPING)))}
    gas = results["EIA gasoline vs CPI Gasoline (SETB01)"]
    rent = results["ZORI vs CPI Rent of primary residence"]

    # gasoline tracks the gasoline stratum well and is stable (unrevised proxy);
    # beta is now ~the mechanical retail->CPI pass-through (>0.5)
    assert gas.proxy_quality == "stable" and gas.r2 > 0.5 and not gas.optimistic
    assert gas.beta > 0.5
    # ZORI does NOT track contemporaneous CPI rent MoM -> unstable (pre-registered H2),
    # and is optimism-flagged (revised_latest_only)
    assert rent.proxy_quality == "unstable" and rent.r2 < 0.1 and rent.optimistic
    # monitors are never regressed
    assert results["Indeed wage tracker"].proxy_quality == "monitor"
    # skipped_months are counted, never imputed (shutdown/series-start)
    assert rent.skipped_months >= 0 and gas.skipped_months >= 0
