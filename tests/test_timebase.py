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
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from nowcast.timebase import (
    NoMomExists,
    NotYetReleased,
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


def test_series_start_boundary(tb):
    series = "CPIAUCSL"
    start = tb.conn.execute(
        "SELECT MIN(reference_period) FROM first_release WHERE series_id=?", (series,)
    ).fetchone()[0]
    long_after = dt.datetime(2026, 1, 1, tzinfo=ET)
    # asof_mom_for_ref on the series-start month -> NoMomExists (structural absence)
    with pytest.raises(NoMomExists):
        tb.asof_mom_for_ref(series, start, long_after)
    # asof_mom just skips it and returns some later, observable MoM
    assert isinstance(tb.asof_mom(series, long_after), float)


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
