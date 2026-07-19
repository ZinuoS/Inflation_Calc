"""Tests for the vintage-safe within-vintage MoM (first_release_mom).

The trap this guards: differencing first-release LEVELS across adjacent months
fabricates a fake MoM whenever a base re-referencing or a seasonal-factor
restatement lands between the two releases -- t and t-1 then sit on different
bases. first_release_mom reads BOTH levels from the single vintage published at
t's first release, so the ratio is base-consistent.

Test (a) is synthetic and self-contained (always runs). Test (b) is against the
real nowcast.sqlite and skips if it hasn't been built.
"""

import sqlite3
from pathlib import Path

import pytest

from nowcast.views import create_views

DB = Path(__file__).parent.parent / "data" / "db" / "nowcast.sqlite"


# ---------- (a) synthetic 2x re-referencing ----------

def _synthetic_db(tmp_path: Path) -> Path:
    """A 3-month series with TRUE MoM = +1%/month, hit by a 2x re-referencing
    published at March's release: Jan/Feb get restated onto the new (half) base
    in the vintage that first carries March.
    """
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
        # ref, vintage_start, vintage_end, value
        # Jan: old base 100 (current until the re-referencing), then restated 50
        ("2020-01-01", "2020-02-15", "2020-04-14", 100.0),
        ("2020-01-01", "2020-04-15", "9999-12-31", 50.0),
        # Feb: old base 101, then restated 50.5
        ("2020-02-01", "2020-03-15", "2020-04-14", 101.0),
        ("2020-02-01", "2020-04-15", "9999-12-31", 50.5),
        # Mar: first released ON the new base at 51.005 (= 102.01 / 2)
        ("2020-03-01", "2020-04-15", "9999-12-31", 51.005),
    ]
    for i, (ref, vin, vend, val) in enumerate(rows, start=1):
        conn.execute(
            "INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?,?)",
            (i, "Z", "Z", ref, vin, vend, val, 1, "TO_VERIFY", None),
        )
    conn.commit()
    conn.close()
    return db


def test_within_vintage_mom_survives_rereferencing(tmp_path):
    db = _synthetic_db(tmp_path)
    create_views(db)
    conn = sqlite3.connect(db)

    wv = dict(conn.execute("SELECT reference_period, mom FROM first_release_mom").fetchall())
    # within-vintage: clean +1% every month (both levels read from the same vintage)
    assert wv["2020-02-01"] == pytest.approx(0.01, abs=1e-6)
    assert wv["2020-03-01"] == pytest.approx(0.01, abs=1e-6)

    # naive cross-vintage differencing of first-release LEVELS: broken at March
    fr = dict(conn.execute("SELECT reference_period, first_release_value FROM first_release").fetchall())
    naive_mar = fr["2020-03-01"] / fr["2020-02-01"] - 1.0
    assert naive_mar < -0.4                       # ~ -49.5% fabricated artifact
    assert abs(naive_mar - wv["2020-03-01"]) > 0.4  # the rule is what fixes it
    conn.close()


# ---------- (b) real data: continuity through known events ----------

def _mom(conn, series, ref):
    r = conn.execute(
        "SELECT mom FROM first_release_mom WHERE series_id=? AND reference_period=?", (series, ref)
    ).fetchone()
    return r[0] if r else None


def _naive_mom(conn, series, ref):
    lt = conn.execute(
        "SELECT first_release_value FROM first_release WHERE series_id=? AND reference_period=?",
        (series, ref),
    ).fetchone()
    prev = conn.execute("SELECT date(?, '-1 month')", (ref,)).fetchone()[0]
    lp = conn.execute(
        "SELECT first_release_value FROM first_release WHERE series_id=? AND reference_period=?",
        (series, prev),
    ).fetchone()
    return (lt[0] / lp[0] - 1.0) if (lt and lp) else None


@pytest.mark.skipif(not DB.exists(), reason="nowcast.sqlite not built")
def test_first_release_mom_omissions_are_all_principled():
    """Delta audit (Amendment A.1). first_release_mom has fewer rows than
    first_release; every omission must be explainable, or it is a silent bug.

    NOTE the Checkpoint-1 premise correction: the omissions are NOT 'one per series
    at its minimum'. They decompose into three principled categories, and this test
    fails on any omission outside them:
      (a) series-start   -- ref is the series' minimum (no t-1). Exactly one/series.
      (b) reference gap  -- t-1 (ref minus one month) was never released (e.g. the
          2025 government shutdown dropped 2025-10 for most CPI series -> no 2025-11 MoM).
      (c) vintage discontinuity -- t-1 exists but shares no vintage window with t's
          first-release vintage (e.g. CPIAUCSL 1970-12, whose earliest ALFRED vintage
          1972-07-21 has no matching 1970-11 vintage). Correct to omit: no common base.
    """
    conn = sqlite3.connect(DB)
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='first_release_mom'").fetchone():
        pytest.skip("views not present")
    omitted = conn.execute(
        """SELECT fr.series_id, fr.reference_period, fr.first_release_vintage
           FROM first_release fr
           LEFT JOIN first_release_mom m
             ON m.series_id = fr.series_id AND m.reference_period = fr.reference_period
           WHERE m.reference_period IS NULL"""
    ).fetchall()

    n_series = conn.execute("SELECT COUNT(DISTINCT series_id) FROM first_release").fetchone()[0]
    cat = {"a_series_start": 0, "b_reference_gap": 0, "c_vintage_discontinuity": 0}
    unexplained = []
    for series_id, ref, vintage in omitted:
        series_min = conn.execute(
            "SELECT MIN(reference_period) FROM first_release WHERE series_id=?", (series_id,)
        ).fetchone()[0]
        prev = conn.execute("SELECT date(?, '-1 month')", (ref,)).fetchone()[0]
        prev_exists = conn.execute(
            "SELECT 1 FROM first_release WHERE series_id=? AND reference_period=?", (series_id, prev)
        ).fetchone()
        prev_vintage_active = conn.execute(
            """SELECT 1 FROM observations WHERE series_id=? AND reference_period=?
               AND observed_asof_vintage<=? AND vintage_end>=? AND _superseded_by_run_id IS NULL""",
            (series_id, prev, vintage, vintage),
        ).fetchone()
        if ref == series_min:
            cat["a_series_start"] += 1
        elif not prev_exists:
            cat["b_reference_gap"] += 1
        elif not prev_vintage_active:
            cat["c_vintage_discontinuity"] += 1
        else:
            unexplained.append((series_id, ref))  # t-1 present AND shares a vintage -> BUG

    assert not unexplained, f"unexplained MoM omissions (silent bug): {unexplained}"
    # every series contributes exactly its start boundary
    assert cat["a_series_start"] == n_series, cat
    # and every omitted row was categorised
    assert sum(cat.values()) == len(omitted)
    conn.close()


@pytest.mark.skipif(not DB.exists(), reason="nowcast.sqlite not built")
def test_pce_mom_continuous_through_rereferencing():
    conn = sqlite3.connect(DB)
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='first_release_mom'").fetchone():
        pytest.skip("first_release_mom view not present")
    # PCEPILFE hit the BEA comprehensive re-referencing at vintage 2023-09-29,
    # which lands on reference month 2023-08's first release.
    for ref in ("2023-06-01", "2023-07-01", "2023-08-01", "2023-09-01"):
        wv = _mom(conn, "PCEPILFE", ref)
        assert wv is not None and abs(wv) < 0.01, f"{ref}: within-vintage MoM {wv} not continuous"
    # and prove the fix matters: naive differencing IS broken at 2023-08
    assert abs(_naive_mom(conn, "PCEPILFE", "2023-08-01")) > 0.01
    conn.close()


@pytest.mark.skipif(not DB.exists(), reason="nowcast.sqlite not built")
def test_cpi_mom_continuous_through_february_restatement():
    conn = sqlite3.connect(DB)
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='first_release_mom'").fetchone():
        pytest.skip("first_release_mom view not present")
    # CPI SA history is restated each February with revised seasonal factors; the
    # January reference (released in February) is where naive differencing leaks.
    for ref in ("2023-12-01", "2024-01-01", "2024-02-01"):
        wv = _mom(conn, "CPIAUCSL", ref)
        assert wv is not None and abs(wv) < 0.01, f"{ref}: within-vintage MoM {wv} not continuous"
    # within-vintage differs from naive at the restated month (leak avoided)
    assert _mom(conn, "CPIAUCSL", "2024-01-01") != pytest.approx(
        _naive_mom(conn, "CPIAUCSL", "2024-01-01"), abs=1e-9
    )
    conn.close()
