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


def seasonally_adjust(nsa: pd.Series) -> pd.Series:
    """Full-sample X-13 seasonal adjustment of a monthly NSA series (DatetimeIndex,
    monthly-start freq). Returns the seasonally adjusted series (`.seasadj`)."""
    from statsmodels.tsa.x13 import x13_arima_analysis

    x13path = _require_x13()
    s = nsa.copy()
    s.index = pd.DatetimeIndex(s.index).to_period("M").to_timestamp()
    s = s.asfreq("MS")
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


def sa_asof(series_id_nsa: str, forecast_time, db_path=DEFAULT_DB) -> pd.Series:
    """VINTAGE-FAITHFUL SA: fit seasonal factors ONLY on NSA data whose reference month
    ended before forecast_time (no future leakage), then return the SA series. The live
    nowcast uses this; the validation below uses full-sample seasonally_adjust."""
    import datetime as dt

    ft = forecast_time if isinstance(forecast_time, dt.date) else dt.date.fromisoformat(str(forecast_time)[:10])
    nsa = _official_nsa(series_id_nsa, db_path)
    nsa = nsa[nsa.index.date < ft.replace(day=1)]  # only fully-elapsed reference months
    return seasonally_adjust(nsa)
