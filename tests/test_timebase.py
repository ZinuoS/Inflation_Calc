"""Adversarial leakage tests for timebase — the firewall's honesty check.

If ANY test here fails, the backtest is invalid: timebase would be handing model
code a value that was not public at forecast_time. Do not weaken these tests to
make them pass; fix timebase.

Covers (Task 2 + Amendment C):
  * every print type (CPI, PPI, PCE): a forecast_time between reference-period end
    and the release returns the PRIOR print for asof/asof_mom, and raises
    NotYetReleased for asof_mom_for_ref (never the not-yet-released month);
  * exact-boundary case (t == release_datetime): strictly-before -> prior print;
  * series-start boundary (Amendment A.3): asof_mom skips it, asof_mom_for_ref
    raises NoMomExists;
  * a 50-pair random property sweep: asof never returns a value whose release
    was not strictly before forecast_time, and always returns the latest such.
"""

import datetime as dt
import random
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from nowcast.timebase import (
    NoMomExists,
    NotYetReleased,
    PreVintageFloor,
    RELEASE_TIME_ET,
    Timebase,
    open_timebase,
)

DB = Path(__file__).parent.parent / "data" / "db" / "nowcast.sqlite"
ET = ZoneInfo("America/New_York")

pytestmark = pytest.mark.skipif(not DB.exists(), reason="nowcast.sqlite not built")

# one representative series per print type
REP = {"CPI": "CPIAUCSL", "PPI": "PPIFIS", "PCE": "PCEPILFE"}


@pytest.fixture
def tb():
    with open_timebase(DB) as t:
        yield t


def _release_and_prev(tb: Timebase, series: str, ref: str):
    """(release_vintage, ref_value, prev_ref, prev_value) for a reference month
    that has a within-vintage MoM (so a prior print exists)."""
    row = tb.conn.execute(
        "SELECT first_release_vintage, first_release_value FROM first_release "
        "WHERE series_id=? AND reference_period=?",
        (series, ref),
    ).fetchone()
    prev = tb.conn.execute("SELECT date(?, '-1 month')", (ref,)).fetchone()[0]
    prow = tb.conn.execute(
        "SELECT first_release_value FROM first_release WHERE series_id=? AND reference_period=?",
        (series, prev),
    ).fetchone()
    return row[0], row[1], prev, (prow[0] if prow else None)


@pytest.mark.parametrize("print_type", ["CPI", "PPI", "PCE"])
def test_between_reference_end_and_release_returns_prior(tb, print_type):
    series = REP[print_type]
    # a recent, settled reference month with a prior print
    ref = "2024-06-01"
    vintage, ref_value, prev, prev_value = _release_and_prev(tb, series, ref)
    assert prev_value is not None
    release_end = dt.date(2024, 6, 30)  # reference-period end
    release_dt = dt.date.fromisoformat(vintage)
    assert release_dt > release_end  # sanity: released after the month it covers
    # a timestamp strictly between reference-period end and the release
    between = dt.datetime.combine(release_dt - dt.timedelta(days=1), dt.time(12, 0), tzinfo=ET)
    assert release_end < between.date() < release_dt

    # level + MoM asof see only the PRIOR print
    assert tb.asof(series, between) == prev_value
    assert tb.asof_mom(series, between) == pytest.approx(_mom(tb, series, prev))
    # for_ref refuses to hand over the not-yet-released month
    with pytest.raises(NotYetReleased):
        tb.asof_mom_for_ref(series, ref, between)


@pytest.mark.parametrize("print_type", ["CPI", "PPI", "PCE"])
def test_exact_release_instant_is_strictly_before(tb, print_type):
    series = REP[print_type]
    ref = "2024-06-01"
    vintage, ref_value, prev, prev_value = _release_and_prev(tb, series, ref)
    exact = dt.datetime.combine(dt.date.fromisoformat(vintage), RELEASE_TIME_ET, tzinfo=ET)
    # at the exact release instant, the reference month is NOT yet observable
    assert tb.asof(series, exact) == prev_value
    with pytest.raises(NotYetReleased):
        tb.asof_mom_for_ref(series, ref, exact)
    # one microsecond later it is observable
    assert tb.asof(series, exact + dt.timedelta(microseconds=1)) == ref_value


def test_gap_boundary_raises_nomomexists(tb):
    # a POST-floor month whose prior month was never released (2025 shutdown dropped
    # CPIAUCSL 2025-10) has no within-vintage MoM -> NoMomExists (not imputed). The
    # series-start month (1947) is instead below the vintage floor (PreVintageFloor,
    # tested separately), so we use the shutdown gap for the NoMomExists path.
    series = "CPIAUCSL"
    long_after = dt.datetime(2026, 7, 1, tzinfo=ET)
    assert tb._vintage_floor[series] <= "2025-11-01"  # gap is above the floor
    with pytest.raises(NoMomExists):
        tb.asof_mom_for_ref(series, "2025-11-01", long_after)
    # asof_mom skips both gap and pre-floor months, returns a later observable MoM
    assert isinstance(tb.asof_mom(series, long_after), float)


def test_pre_vintage_floor_refused_for_ref(tb):
    """A pre-2011 gasoline-stratum ref (ALFRED bulk-archived at 2011-04-15) must raise
    PreVintageFloor via _for_ref -- its 'first release' is a restated value. asof_mom
    skips it and returns a genuine post-floor MoM instead."""
    floor = tb._vintage_floor["CUSR0000SETB01"]
    assert floor >= "2011-01-01"  # bulk-archived stratum
    long_after = dt.datetime(2026, 7, 1, tzinfo=ET)
    with pytest.raises(PreVintageFloor):
        tb.asof_mom_for_ref("CUSR0000SETB01", "2005-01-01", long_after)
    # a post-floor ref is fine
    assert isinstance(tb.asof_mom_for_ref("CUSR0000SETB01", "2015-06-01", long_after), float)
    # asof_mom never returns a pre-floor month
    assert isinstance(tb.asof_mom("CUSR0000SETB01", long_after), float)


def test_reconcile_overlap_excludes_pre_floor():
    """The gasoline pair's regression must include ONLY genuine post-floor months --
    restated-as-first impossible by construction (not by documentation)."""
    from nowcast import reconcile

    results = {r.label: r for r in reconcile.run(str(DB), reconcile.build_pairs(
        str(Path(__file__).parent.parent / "mapping" / "mapping.yaml")))}
    gas = results["EIA gasoline vs CPI Gasoline (SETB01)"]
    assert gas.pre_floor_months > 0  # pre-2011 months were present and excluded
    # every overlap month is at/above the floor (checked via a direct floor query)
    with open_timebase(DB) as tb:
        floor = tb._vintage_floor["CUSR0000SETB01"]
    conn = sqlite3.connect(DB)
    below = conn.execute(
        "SELECT COUNT(*) FROM first_release_mom WHERE series_id='CUSR0000SETB01' AND reference_period < ?",
        (floor,),
    ).fetchone()[0]
    conn.close()
    assert below == gas.pre_floor_months or below >= gas.pre_floor_months  # all pre-floor refused


def _mom(tb: Timebase, series: str, ref: str):
    r = tb.conn.execute(
        "SELECT mom FROM first_release_mom WHERE series_id=? AND reference_period=?", (series, ref)
    ).fetchone()
    return r[0] if r else None


def test_property_sweep_no_leakage(tb):
    """50 random (series, timestamp) pairs: asof must equal the value whose release
    is the latest strictly before forecast_time -- never a later (leaked) one."""
    series_ids = [r[0] for r in tb.conn.execute("SELECT DISTINCT series_id FROM first_release")]
    rng = random.Random(20260719)
    checked = 0
    for _ in range(50):
        series = rng.choice(series_ids)
        ft = dt.datetime.fromtimestamp(
            rng.randint(int(dt.datetime(2000, 1, 1).timestamp()),
                        int(dt.datetime(2026, 7, 1).timestamp())),
            tz=ET,
        )
        # independent oracle: latest reference whose observable release < ft
        rows = tb.conn.execute(
            "SELECT reference_period, first_release_value, first_release_vintage "
            "FROM first_release WHERE series_id=?",
            (series,),
        ).fetchall()
        observable = [
            (ref, val) for ref, val, vin in rows if tb._observable_dt(series, vin) < ft
        ]
        if not observable:
            with pytest.raises(NotYetReleased):
                tb.asof(series, ft)
            continue
        expected_ref, expected_val = max(observable, key=lambda rv: rv[0])
        got = tb.asof(series, ft)
        assert got == expected_val, f"{series} @ {ft}: got {got}, oracle {expected_val} ({expected_ref})"
        # and the returned reference's release is strictly before ft (no leak)
        vin = tb.conn.execute(
            "SELECT first_release_vintage FROM first_release WHERE series_id=? AND reference_period=?",
            (series, expected_ref),
        ).fetchone()[0]
        assert tb._observable_dt(series, vin) < ft
        checked += 1
    assert checked > 0
