"""Monthly alignment of proxy series to BLS reference conventions (Session 2B, Task 2).

Deterministic, offline (rule 4): reads proxy_observations via db.connect, returns
monthly-aligned levels keyed by first-of-month. No network, no fitting.

Convention choices (each cited):

* Weekly / daily energy -> monthly MEAN of within-month observations.
  BLS collects CPI prices throughout the reference month and the monthly index
  reflects that within-month price experience (BLS Handbook of Methods, CPI,
  ch. "Calculation" — prices are collected across the entire month). The standard
  alignment of a higher-frequency retail-price series (EIA weekly gasoline, daily
  heating-oil) to that convention is the simple monthly average of the
  within-month observations. This mirrors how FRED derives GASREGM (monthly) from
  GASREGW (weekly). We use an unweighted mean; BLS's own within-month collection is
  approximately uniform, so day-weighting is second-order and not imposed.

* Already-monthly proxies (ZORI, wage trackers) -> identity. ZORI's month-end date
  is normalized to first-of-month at fetch; the value passes through.

* Manheim mid-month vs full-month MUST be kept as DISTINCT series (not averaged):
  the mid-month release is a genuine early signal and the full-month is the settled
  value; collapsing them destroys the lead information (research plan H1). Manheim
  is Group B (not yet ingested); this rule is recorded here as the binding
  convention for when it lands — its two releases enter proxy_observations under
  distinct series_key values and align independently.

MoM: monthly level ratio minus 1, within the aligned monthly series (a proxy is a
single revised/unrevised series, so there is no vintage subtlety on the proxy side;
the vintage discipline lives on the OFFICIAL side, read via timebase).
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from nowcast import db

MONTHLY = "monthly"
AVERAGED_FREQUENCIES = ("weekly", "daily")


def monthly_levels(db_path, source: str, series_key: str) -> dict[str, float]:
    """Return {first-of-month ISO: aligned level} for one proxy series."""
    with db.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT period, value, frequency FROM proxy_observations "
            "WHERE source = ? AND series_key = ? AND _superseded_by_run_id IS NULL",
            (source, series_key),
        ).fetchall()
    if not rows:
        return {}
    freq = rows[0][2]
    if freq == MONTHLY:
        # already monthly; period is first-of-month
        return {p: float(v) for p, v, _ in rows}
    if freq in AVERAGED_FREQUENCIES:
        buckets: dict[str, list[float]] = defaultdict(list)
        for period, value, _ in rows:
            month = dt.date.fromisoformat(period).replace(day=1).isoformat()
            buckets[month].append(float(value))
        return {m: sum(vs) / len(vs) for m, vs in buckets.items()}
    raise ValueError(f"unknown frequency {freq!r} for {source}/{series_key}")


def monthly_mom(db_path, source: str, series_key: str) -> dict[str, float]:
    """Proxy MoM by reference month: level_t / level_{t-1} - 1, on the aligned
    monthly series. Only consecutive months (no gap) produce a MoM."""
    levels = monthly_levels(db_path, source, series_key)
    out: dict[str, float] = {}
    for period in levels:
        d = dt.date.fromisoformat(period)
        prev = (d.replace(day=1) - dt.timedelta(days=1)).replace(day=1).isoformat()
        if prev in levels and levels[prev] != 0:
            out[period] = levels[period] / levels[prev] - 1.0
    return out
