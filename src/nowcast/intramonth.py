"""Intramonth nowcast-as-of-day monitor (Session 4, Task 5). Deterministic, offline.

For any date D in (or around) reference month M, the current best estimate of the print, using
EXACTLY the information observable at D — proxies gated by proxy_timebase, aggregated by the
H8 window (component_models), stratum history limited to already-printed months. As D advances
the within-month proxy paths fill in and the estimate converges.

The FREEZE is enforced, not just documented: per the availability calendar nothing useful
arrives after T-4 (the last Manheim full-month / NADAC update lands ~4 days before the CPI
print), so any as-of date later than T-4 returns the T-4 estimate unchanged. `backtest_curve`
gives the honest "how early do we know what we know" — MAE as a function of days-to-release.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np

from nowcast import component_models as CM
from nowcast import db

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"
FREEZE_LEAD_DAYS = 4        # T-4: last useful input arrival (availability_calendar); freeze after


def _release_date(conn, ref_month: str) -> dt.date | None:
    r = conn.execute("SELECT release_date FROM release_calendar WHERE print='CPI' AND "
                     "reference_period=? AND _superseded_by_run_id IS NULL", (ref_month,)).fetchone()
    return dt.date.fromisoformat(r[0]) if r else None


def _actual_nsa(conn, sid: str, m: str) -> float | None:
    def add(x, k):
        d = dt.date.fromisoformat(x); mo = d.month - 1 + k
        return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()
    px = {p: float(v) for p, v in conn.execute(
        "SELECT period, value FROM official_current WHERE series_id=? AND period IN (?,?) "
        "AND _superseded_by_run_id IS NULL", (sid, m, add(m, -1)))}
    pm = add(m, -1)
    return (px[m] / px[pm] - 1.0) if (m in px and pm in px and px[pm]) else None


def nowcast_as_of(ref_month: str, as_of, aggregate: str = "headline", db_path=DEFAULT_DB) -> dict:
    """Best estimate of the aggregate NSA MoM print for ref_month, using only info observable at
    as_of. Freeze enforced: as_of beyond T-4 is clamped to the T-4 date."""
    as_of = as_of if isinstance(as_of, dt.date) else dt.date.fromisoformat(str(as_of)[:10])
    with db.connect(db_path) as conn:
        rel = _release_date(conn, ref_month)
    frozen = False
    eff = as_of
    if rel is not None:
        freeze_date = rel - dt.timedelta(days=FREEZE_LEAD_DAYS)
        if as_of > freeze_date:
            eff, frozen = freeze_date, True
    r = CM.forecast_aggregate_nsa(ref_month, eff, aggregate, db_path=db_path)
    return {"ref_month": ref_month, "as_of": as_of.isoformat(), "effective_asof": eff.isoformat(),
            "frozen": frozen, "forecast_mom": r["forecast_mom"],
            "n_proxy_driven": r.get("n_proxy_driven"), "days_to_release": (rel - as_of).days if rel else None}


def tminus_path(ref_month: str, aggregate: str = "headline", tmax: int = 30, tmin: int = 3,
                db_path=DEFAULT_DB) -> list[dict]:
    """The T-minus path: estimate at each day from T-tmax to T-tmin before the print."""
    with db.connect(db_path) as conn:
        rel = _release_date(conn, ref_month)
    if rel is None:
        return []
    return [nowcast_as_of(ref_month, rel - dt.timedelta(days=d), aggregate, db_path)
            for d in range(tmax, tmin - 1, -1)]


def backtest_curve(aggregate: str = "headline", n_prints: int = 18, tmax: int = 30, tmin: int = 3,
                   db_path=DEFAULT_DB) -> dict:
    """For the last `n_prints` evaluable CPI prints, the MAE of the as-of-day nowcast vs the
    realized first-release NSA MoM, as a function of days-to-release."""
    tgt = "CUUR0000SA0" if aggregate == "headline" else "CUUR0000SA0L1E"
    with db.connect(db_path) as conn:
        months = [r[0] for r in conn.execute(
            "SELECT reference_period FROM release_calendar WHERE print='CPI' AND "
            "release_date<=? AND _superseded_by_run_id IS NULL ORDER BY reference_period DESC LIMIT ?",
            (dt.date.today().isoformat(), n_prints + 6))]
        actuals = {m: _actual_nsa(conn, tgt, m) for m in months}
    months = [m for m in months if actuals.get(m) is not None][:n_prints]
    by_day: dict[int, list[float]] = {d: [] for d in range(tmax, tmin - 1, -1)}
    for m in months:
        for p in tminus_path(m, aggregate, tmax, tmin, db_path):
            if p["forecast_mom"] is not None:
                by_day[p["days_to_release"]].append(abs(p["forecast_mom"] - actuals[m]) * 10000)
    curve = {d: round(float(np.mean(v)), 2) for d, v in by_day.items() if v}
    return {"aggregate": aggregate, "n_prints": len(months), "months": months,
            "mae_by_days_to_release": curve, "freeze_lead_days": FREEZE_LEAD_DAYS}
