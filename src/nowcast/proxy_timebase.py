"""Proxy-side information-timing firewall (Session 3B, Task 2d). Deterministic, offline.

The mirror of the official-side `timebase`: for alternative-data proxies it materializes, per
observation, an `observed_asof` = the earliest wall-clock date a real-time user could have had
that value, from the source's DOCUMENTED, CITED publication rule (spec.yaml `publication`
block). `proxy_asof(source, forecast_time)` returns ONLY observations with
observed_asof <= forecast_time. **Session 4 feature construction MUST read proxies through
`proxy_asof` — never `proxy_observations` directly** (the standing rule; see
docs/proxy_timing_audit.md), exactly as backtests read the official side through timebase.

Why rule-based, not a stored column: for most proxies the true per-observation press date is
not recorded across full history (only publication SCHEDULES are documented). The rule is the
honest, auditable materialization — verified against real dates in the audit doc. For
revised_latest_only sources the observed_asof is explicitly ESTIMATED (documented lag + a one-
week conservatism margin) — one more reason those carry optimism flags.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

from nowcast import db

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "db" / "nowcast.sqlite"
PIPELINES = REPO / "pipelines"


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def _month_end(d: dt.date) -> dt.date:
    nxt = dt.date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
    return nxt - dt.timedelta(days=1)


def _add_months(d: dt.date, k: int) -> dt.date:
    mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1)


_SPEC_CACHE: dict[str, dict] = {}


def _spec_for_source(source: str) -> dict:
    """Find the pipeline spec whose `source:` field == source (the dir name may differ,
    e.g. source 'sp500' lives in pipelines/equity_path)."""
    if source in _SPEC_CACHE:
        return _SPEC_CACHE[source]
    # fast path: dir named after the source
    direct = PIPELINES / source / "spec.yaml"
    if direct.exists():
        s = yaml.safe_load(direct.read_text())
        if s.get("source") == source:
            _SPEC_CACHE[source] = s
            return s
    for sp in PIPELINES.glob("*/spec.yaml"):
        s = yaml.safe_load(sp.read_text())
        if s.get("source") == source:
            _SPEC_CACHE[source] = s
            return s
    raise ValueError(f"proxy_timebase: no pipeline spec with source={source}")


def publication_block(source: str) -> dict:
    """The source's `publication` metadata from its spec.yaml (Task 2d part a)."""
    pub = _spec_for_source(source).get("publication")
    if pub is None:
        raise ValueError(f"proxy_timebase: source {source} spec has no `publication` block (Task 2d)")
    return pub


def observed_asof(source: str, period: str, pub: dict | None = None) -> dt.date:
    """Materialize observed_asof for one observation from the source's publication rule.
    `period` is the observation date (weekly/daily) or first-of-month (monthly)."""
    pub = pub or publication_block(source)
    rule = pub["rule"]
    p = _d(period)
    lag = int(pub.get("lag_days", 0))
    if rule == "same_day":                       # sp500 daily close
        return p
    if rule == "eia_weekly":                      # Monday price, published Mon PM / Tue AM
        return p + dt.timedelta(days=lag or 1)
    if rule == "daily_next_bday":                 # daily spot, next business day
        nxt = p + dt.timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += dt.timedelta(days=1)
        return nxt
    if rule == "manheim_full_month":              # ref month M index published early M+1
        return _add_months(p, 1) + dt.timedelta(days=lag or 6)
    if rule == "manheim_mid_month":               # mid-month update ~17th of M
        return p + dt.timedelta(days=lag or 16)
    if rule == "nadac_weekly":                    # monthly complete once M's last week posts (~Wed)
        return _month_end(p) + dt.timedelta(days=lag or 7)
    if rule == "tsa_month_end":                   # complete-month avg available day after month end
        return _month_end(p) + dt.timedelta(days=lag or 1)
    if rule == "monthly_release_lag":             # revised_latest_only: end-of-month + documented lag
        return _month_end(p) + dt.timedelta(days=lag)
    raise ValueError(f"proxy_timebase: unknown publication rule {rule!r} for {source}")


def proxy_asof(source: str, forecast_time, series_key: str | None = None,
               db_path=DEFAULT_DB) -> dict[str, float]:
    """{period: value} for observations of `source` whose observed_asof <= forecast_time.
    THE Session-4 proxy read path (firewall). forecast_time: date or ISO string."""
    ft = forecast_time if isinstance(forecast_time, dt.date) else _d(str(forecast_time))
    pub = publication_block(source)
    with db.connect(db_path) as conn:
        q = ("SELECT period, value, series_key FROM proxy_observations WHERE source=? "
             "AND _superseded_by_run_id IS NULL")
        args: list = [source]
        if series_key is not None:
            q += " AND series_key=?"; args.append(series_key)
        rows = conn.execute(q, args).fetchall()
    out: dict[str, float] = {}
    for period, value, _sk in rows:
        if observed_asof(source, period, pub) <= ft:
            out[period] = value
    return dict(sorted(out.items()))


def latest_asof(source: str, forecast_time, series_key: str | None = None, db_path=DEFAULT_DB):
    """(period, value) of the most recent observation available at forecast_time, or None."""
    got = proxy_asof(source, forecast_time, series_key, db_path)
    return (max(got), got[max(got)]) if got else None
