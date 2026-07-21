"""X-13ARIMA-SEATS seasonal adjustment wrapper (Session 3A, Task 3).

Methodology replication: BLS seasonally adjusts selected CPI series with the Census
Bureau's X-13ARIMA-SEATS (BLS Handbook of Methods, CPI ch. 17, "Seasonal adjustment").
We wrap statsmodels' X-13 interface — never a substitute method. If the x13as binary is
absent the caller gets a clear error, never a silently different SA.

Two modes:
- seasonally_adjust(nsa): full-sample SA, for the methodology-side validation against
  BLS published SA (reads official_current NSA/SA, no vintage).
- sa_asof(series_id, forecast_time): VINTAGE-FAITHFUL — the NSA information set is
  truncated to what was observable strictly before forecast_time (via timebase's release
  logic) BEFORE fitting, so seasonal factors never see the future. This is the mode the
  live nowcast uses.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pandas as pd

from nowcast import db

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"


def x13_binary() -> str | None:
    """Directory containing the x13as binary, from X13PATH or PATH; None if absent.
    statsmodels locates the binary the same way (x12path arg / X13PATH env)."""
    env = os.environ.get("X13PATH")
    if env and (Path(env) / "x13as").exists():
        return env
    found = shutil.which("x13as") or shutil.which("x13ashtml")
    return str(Path(found).parent) if found else None


class X13Unavailable(RuntimeError):
    """The x13as binary is not installed / not on PATH or X13PATH."""


def _require_x13() -> str:
    p = x13_binary()
    if p is None:
        raise X13Unavailable(
            "x13as binary not found on PATH or X13PATH. Install X-13ARIMA-SEATS and either "
            "add it to PATH or set X13PATH to its directory. No SA is computed without it."
        )
    return p


def seasonally_adjust(nsa: pd.Series, max_months: int = 480) -> pd.Series:
    """Full-sample X-13 seasonal adjustment of a monthly NSA series (DatetimeIndex,
    monthly-start freq). Returns the seasonally adjusted series (`.seasadj`)."""
    from statsmodels.tsa.x13 import x13_arima_analysis

    x13path = _require_x13()
    s = nsa.copy().sort_index()
    s.index = pd.DatetimeIndex(s.index).to_period("M").to_timestamp()
    s = s[~s.index.duplicated()].asfreq("MS")  # monthly grid; NaN marks gaps
    # X-13 requires a contiguous series (no internal NaN). Use the LONGEST contiguous
    # run — for a recent one-month gap (e.g. the 2025 shutdown) that keeps the long
    # pre-gap history, which still covers the trailing validation window.
    if s.isna().any():
        grp = s.notna().ne(s.notna().shift()).cumsum()
        run_id = s[s.notna()].groupby(grp).size().idxmax()
        s = s[grp == run_id].dropna()
    # X-13 caps a series at 1020 observations; use the most recent `max_months` (40y is
    # ample for stable seasonal factors and covers any trailing validation window).
    if len(s) > max_months:
        s = s.iloc[-max_months:]
    res = x13_arima_analysis(s, x12path=x13path, prefer_x13=True, log=None)
    return res.seasadj


def _official_nsa(series_id_nsa: str, db_path=DEFAULT_DB) -> pd.Series:
    """Monthly NSA level series from official_current (methodology side)."""
    with db.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT period, value FROM official_current "
            "WHERE series_id = ? AND _superseded_by_run_id IS NULL ORDER BY period",
            (series_id_nsa,),
        ).fetchall()
    idx = pd.to_datetime([r[0] for r in rows])
    return pd.Series([r[1] for r in rows], index=idx)


def sa_replication_mae(item_code: str, years: int = 8, db_path=DEFAULT_DB) -> dict:
    """Our X-13 SA of the NSA series vs BLS PUBLISHED SA, MoM MAE in bp over the trailing
    `years` (BLS Handbook, CPI ch.17). This residual is the SA replication FLOOR for the
    stratum — the irreducible gap between our default X-13 and BLS's per-series-tuned SA;
    it bounds achievable MoM accuracy for that stratum. Returns MAE_bp, n, and correlation."""
    import numpy as np

    nsa = _official_nsa(f"CUUR0000{item_code}", db_path).sort_index()
    bls_sa = _official_nsa(f"CUSR0000{item_code}", db_path).sort_index()
    if len(nsa) < 60 or len(bls_sa) < 60:
        return {"item_code": item_code, "error": "insufficient NSA/SA history"}
    our_sa = seasonally_adjust(nsa)
    our_mom = our_sa.pct_change()
    bls_mom = bls_sa.pct_change()
    cutoff = pd.Timestamp.today().normalize() - pd.DateOffset(years=years)
    idx = our_mom.index.intersection(bls_mom.index)
    idx = idx[idx >= cutoff]
    a = our_mom.reindex(idx).to_numpy()
    b = bls_mom.reindex(idx).to_numpy()
    mask = ~(np.isnan(a) | np.isnan(b))
    a, b = a[mask], b[mask]
    mae_bp = float(np.mean(np.abs(a - b)) * 10000)
    return {"item_code": item_code, "n": int(mask.sum()), "mae_bp": round(mae_bp, 2),
            "corr": round(float(np.corrcoef(a, b)[0, 1]), 4)}


def sa_asof(series_id_nsa: str, forecast_time, db_path=DEFAULT_DB) -> pd.Series:
    """VINTAGE-FAITHFUL SA: fit seasonal factors ONLY on NSA data whose reference month
    ended before forecast_time (no future leakage), then return the SA series. The live
    nowcast uses this; the validation below uses full-sample seasonally_adjust."""
    import datetime as dt

    ft = forecast_time if isinstance(forecast_time, dt.date) else dt.date.fromisoformat(str(forecast_time)[:10])
    nsa = _official_nsa(series_id_nsa, db_path)
    nsa = nsa[nsa.index.date < ft.replace(day=1)]  # only fully-elapsed reference months
    return seasonally_adjust(nsa)
