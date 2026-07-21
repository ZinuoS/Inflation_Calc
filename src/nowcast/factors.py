"""BLS seasonal factors, harvested (not re-estimated) — Session 3A, Task 3b.

The Checkpoint-2 reroute: the nowcast forecasts in NSA space and converts to SA with
BLS's OWN factors, implied_factor = NSA / SA. Rationale (verified, not assumed):

* NSA CPI index values are NEVER revised (BLS Handbook of Methods, CPI ch. 17: only the
  seasonally adjusted series are revised, once a year with updated factors; the NSA index
  is final at first release). VERIFIED empirically here: across 154-183 ALFRED vintages,
  ZERO reference-period NSA values changed for gasoline/used-cars/airfares (the strata
  with NSA archives). So the NSA side needs no vintage — official_current is first-release.
* BLS factors are PREDETERMINED within a year (projected in the February revision, applied
  mechanically thereafter). So the operative floor is factor-EXTRAPOLATION error — how well
  the predetermined factor for a month matches the factor realized at first release — NOT
  our-X13-vs-BLS method residual (which is why we do not re-estimate SA; seasonal.py's own
  X-13 is retained ONLY for proxy de-noising where no official factor exists).

implied_factor(item, month) = NSA / SA. factor_asof(item, target, forecast_time) = the
factor knowable at forecast_time = the latest SAME-CALENDAR-MONTH implied factor from the
vintage then available. Deterministic, offline via db.connect / timebase.

CAVEAT (Checkpoint 3b finding): factor_asof here is CARRY-FORWARD (last year's same-month
factor) — a proxy for BLS's predetermined factor, not that factor itself. BLS publishes its
projected factors and applies them mechanically at first release, so the realized
first-release factor for month M *is* BLS's published projected factor for M. Carry-forward
therefore over-states the extrapolation error (an UPPER BOUND); harvesting BLS's published
projected factor files would drive the ex-February floor toward ~0. See docs/sa_floor.md §4.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from nowcast import db

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"

# item_code -> the SA vintage series in `observations`. Most strata use CUSR0000{code};
# a few CPI aggregates are ALFRED-archived only under FRED alias ids (the raw CU form has
# no vintages), so we point at the alias.
SA_ALIAS = {"SA0": "CPIAUCSL", "SA0L1E": "CPILFESL", "SAA": "CPIAPPSL"}


def sa_series(item_code: str) -> str:
    return SA_ALIAS.get(item_code, f"CUSR0000{item_code}")


def nsa_series(item_code: str) -> str:
    return f"CUUR0000{item_code}"


def _add_months(month: str, k: int) -> str:
    d = dt.date.fromisoformat(month)
    mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def _nsa(conn, item_code: str, month: str) -> float | None:
    r = conn.execute(
        "SELECT value FROM official_current WHERE series_id = ? AND period = ? "
        "AND _superseded_by_run_id IS NULL",
        (nsa_series(item_code), month),
    ).fetchone()
    return r[0] if r else None


def _sa_asof(conn, item_code: str, ref_month: str, forecast_time: str) -> float | None:
    """SA value for ref_month in the vintage active at forecast_time (vintage-safe)."""
    r = conn.execute(
        "SELECT value FROM observations WHERE series_id = ? AND reference_period = ? "
        "AND observed_asof_vintage <= ? AND vintage_end >= ? AND _superseded_by_run_id IS NULL "
        "ORDER BY observed_asof_vintage DESC LIMIT 1",
        (sa_series(item_code), ref_month, forecast_time, forecast_time),
    ).fetchone()
    return r[0] if r else None


def _sa_firstrelease(conn, item_code: str, ref_month: str) -> float | None:
    r = conn.execute(
        "SELECT first_release_value FROM first_release WHERE series_id = ? AND reference_period = ?",
        (sa_series(item_code), ref_month),
    ).fetchone()
    return r[0] if r else None


def implied_factor(item_code: str, month: str, basis: str = "first_release", db_path=DEFAULT_DB) -> float | None:
    """NSA / SA for a reference month. basis: 'first_release' (SA first-release vintage) or
    'latest' (official_current SA). NSA is always first-release (unrevised)."""
    with db.connect(db_path) as conn:
        nsa = _nsa(conn, item_code, month)
        if basis == "latest":
            r = conn.execute(
                "SELECT value FROM official_current WHERE series_id=? AND period=? "
                "AND _superseded_by_run_id IS NULL", (sa_series(item_code), month)).fetchone()
            sa = r[0] if r else None
        else:
            sa = _sa_firstrelease(conn, item_code, month)
    if nsa is None or not sa:
        return None
    return nsa / sa


def _factor_asof_conn(conn, item_code: str, target_month: str, ft: str) -> float | None:
    p = _add_months(target_month, -12)
    for _ in range(20):
        sa = _sa_asof(conn, item_code, p, ft)
        nsa = _nsa(conn, item_code, p)
        if sa and nsa:
            return nsa / sa
        p = _add_months(p, -12)
    return None


def factor_extrapolation_error(item_code: str, years: int = 8, db_path=DEFAULT_DB) -> dict:
    """THE OPERATIVE SA FLOOR (Checkpoint-2 reroute). For each month in the trailing
    window: SA_est = NSA / factor_asof (the predetermined factor, forecast at the month's
    start), its MoM vs the realized first-release SA MoM. MAE in bp, split ex-February vs
    February (where the annual factor revision lands — the 3.5bp exhibit, per stratum).
    The NEW acceptance check is MAE_ex_february < 10 bp/MoM."""
    import numpy as np
    import pandas as pd

    sa = sa_series(item_code)
    cutoff = (pd.Timestamp.today().normalize() - pd.DateOffset(years=years)).date().replace(day=1).isoformat()
    with db.connect(db_path) as conn:
        realized = {m: v for m, v in conn.execute(
            "SELECT reference_period, mom FROM first_release_mom WHERE series_id = ?", (sa,))
            if m >= cutoff}
        months = sorted(realized)
        sa_est: dict[str, float] = {}
        for m in sorted(set(months) | {_add_months(min(months), -1)}) if months else []:
            nsa = _nsa(conn, item_code, m)
            fa = _factor_asof_conn(conn, item_code, m, m)  # forecast_time = first-of-month m
            if nsa is not None and fa:
                sa_est[m] = nsa / fa
    ex_feb, feb = [], []
    for m in months:
        pm = _add_months(m, -1)
        if m in sa_est and pm in sa_est:
            err_bp = abs((sa_est[m] / sa_est[pm] - 1) - realized[m]) * 10000
            (feb if m[5:7] == "02" else ex_feb).append(err_bp)
    def mae(x):
        return round(float(np.mean(x)), 2) if x else None
    return {"item_code": item_code, "n_ex_feb": len(ex_feb), "n_feb": len(feb),
            "mae_ex_feb_bp": mae(ex_feb), "mae_feb_bp": mae(feb), "mae_all_bp": mae(ex_feb + feb)}


def factor_asof(item_code: str, target_month: str, forecast_time, db_path=DEFAULT_DB) -> float | None:
    """The predetermined factor for target_month knowable at forecast_time: the latest
    same-calendar-month implied factor from the vintage then available. Walks back a year
    at a time from target_month to the most recent same-month whose SA is observable
    strictly before forecast_time (BLS's within-year predetermined factor)."""
    ft = forecast_time if isinstance(forecast_time, str) else str(forecast_time)[:10]
    with db.connect(db_path) as conn:
        p = _add_months(target_month, -12)
        for _ in range(20):  # walk back same-calendar-month years
            sa = _sa_asof(conn, item_code, p, ft)
            nsa = _nsa(conn, item_code, p)
            if sa and nsa:
                return nsa / sa
            p = _add_months(p, -12)
    return None


# ---------------------------------------------------------------------------
# HARVESTED published projected factor (Task 3b option a) — the pipeline
# bls_seasonal_factors loads BLS's own projected factor for each month, stamped with
# published_asof (the Jan-YYYY CPI release date it was introduced). This is the factor
# BLS actually applies at first release, so NSA / published_factor reproduces the
# first-release SA to rounding (~0.01 bp), for every month whose year-factors were
# published strictly before forecast_time. January is the boundary: the year's factors
# are introduced simultaneously with January's own release, so a real-time forecaster
# still holds only the PRIOR year's January factor for it (handled by the fallback).
# ---------------------------------------------------------------------------

def _release_date(conn, ref_month: str) -> str | None:
    r = conn.execute(
        "SELECT release_date FROM release_calendar WHERE print='CPI' AND reference_period=? "
        "AND _superseded_by_run_id IS NULL", (ref_month,)).fetchone()
    return r[0] if r else None


def _published_factor_conn(conn, item_code: str, target_month: str, ft: str) -> tuple[float | None, bool]:
    """(factor, in_year): BLS's published projected factor for target_month knowable at
    forecast_time ft. Prefer the target month's OWN published factor if it was introduced
    before ft (in_year=True); else walk back same-calendar-month years to the most recent
    published factor introduced before ft (in_year=False — the January-boundary fallback)."""
    sid = sa_series(item_code)
    p = target_month
    for k in range(21):
        r = conn.execute(
            "SELECT projected_factor FROM bls_seasonal_factors WHERE series_id=? AND "
            "reference_period=? AND published_asof < ? AND _superseded_by_run_id IS NULL "
            "ORDER BY published_asof DESC LIMIT 1", (sid, p, ft)).fetchone()
        if r:
            return r[0], k == 0
        p = _add_months(p, -12)
    return None, False


def published_factor_asof(item_code: str, target_month: str, forecast_time, db_path=DEFAULT_DB) -> float | None:
    """BLS's harvested published projected factor for target_month knowable at
    forecast_time (None if this stratum is indirectly adjusted / not in the factor files)."""
    ft = forecast_time if isinstance(forecast_time, str) else str(forecast_time)[:10]
    with db.connect(db_path) as conn:
        return _published_factor_conn(conn, item_code, target_month, ft)[0]


def factor_conversion_error(item_code: str, years: int = 8, db_path=DEFAULT_DB) -> dict:
    """THE OPERATIVE SA FLOOR with HARVESTED published factors (Task 3b option a). For each
    trailing month, forecast_time = that month's CPI release date; SA_est = NSA /
    published_factor_asof, MoM vs the realized first-release SA MoM. MAE in bp, split
    'in_year' (the month's own current-year projected factor was available before release —
    Feb-Dec) vs 'boundary' (January: fell back to the prior year's published factor).
    Returns None-heavy dict for indirectly-adjusted strata (no direct factor to harvest)."""
    import numpy as np
    import pandas as pd

    sa = sa_series(item_code)
    cutoff = (pd.Timestamp.today().normalize() - pd.DateOffset(years=years)).date().replace(day=1).isoformat()
    with db.connect(db_path) as conn:
        realized = {m: v for m, v in conn.execute(
            "SELECT reference_period, mom FROM first_release_mom WHERE series_id = ?", (sa,))
            if m >= cutoff}
        months = sorted(realized)
        est: dict[str, tuple[float, bool]] = {}
        for m in sorted(set(months) | {_add_months(min(months), -1)}) if months else []:
            ft = _release_date(conn, m) or _add_months(m, 2)  # nowcast up to m's release
            nsa = _nsa(conn, item_code, m)
            f, in_year = _published_factor_conn(conn, item_code, m, ft)
            if nsa is not None and f:
                est[m] = (nsa / f, in_year)
    # A MoM error needs BOTH endpoints. 'clean' = both months carry their own current-year
    # published factor (Mar-Dec). 'boundary' = January itself, or February (whose January
    # base is the pre-annual-update fallback) — the once-a-year seam.
    clean, boundary = [], []
    for m in months:
        pm = _add_months(m, -1)
        if m in est and pm in est:
            err_bp = abs((est[m][0] / est[pm][0] - 1) - realized[m]) * 10000
            (clean if (est[m][1] and est[pm][1]) else boundary).append(err_bp)
    def mae(x):
        return round(float(np.mean(x)), 2) if x else None
    return {"item_code": item_code, "n_clean": len(clean), "n_boundary": len(boundary),
            "mae_clean_bp": mae(clean), "mae_boundary_bp": mae(boundary),
            "mae_all_bp": mae(clean + boundary)}
