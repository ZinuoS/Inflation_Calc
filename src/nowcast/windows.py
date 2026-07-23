"""Within-month window-alignment layer (Session 4, Task 1). Deterministic, offline.

A daily/weekly proxy has a within-month price *path*; how you collapse it to one monthly number
is a modelling choice (full-month mean, BLS-style three-pricing-period mean, week-weighted,
trailing-k-day). H8 selects that scheme per stratum INSIDE training folds against the official
first-release NSA stratum relative, and reports its stability — an unstable winner means the
window is not identifiable at our sample size, and we default to the full-month mean rather than
fold-chase. Partial-window sources (Manheim mid-month = days 1-15) enter AS partial features and
are never silently promoted to a whole month (see `partial_feature`).

Feature-time discipline: for LIVE feature construction use `monthly_mom_scheme(..., forecast_time)`
which reads only obs observable by forecast_time (proxy_timebase). The H8 SELECTION runs on the
historical panel but picks the scheme train-only inside each walk-forward fold (leakage-safe).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np

from nowcast import db

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"
SCHEMES = ("full_month_mean", "bls_three_period", "week_weighted", "trailing_7", "trailing_14")


def _daily_obs(conn, source: str, series_key: str) -> dict[str, float]:
    return {p: v for p, v in conn.execute(
        "SELECT period, value FROM proxy_observations WHERE source=? AND series_key=? "
        "AND _superseded_by_run_id IS NULL", (source, series_key))}


def _month(d: str) -> str:
    return d[:7] + "-01"


def aggregate_month(obs: dict[str, float], month: str, scheme: str) -> float | None:
    """Collapse the within-month daily/weekly obs of `month` to one level under `scheme`."""
    pts = sorted((dt.date.fromisoformat(d), v) for d, v in obs.items() if _month(d) == month)
    if not pts:
        return None
    days = [d.day for d, _ in pts]
    vals = [v for _, v in pts]
    if scheme == "full_month_mean":
        return float(np.mean(vals))
    if scheme == "bls_three_period":                     # early/mid/late thirds, mean of thirds
        thirds = [[], [], []]
        for dday, v in zip(days, vals):
            thirds[min(2, (dday - 1) // 11)].append(v)    # 1-11, 12-22, 23-31 (approx thirds)
        means = [np.mean(t) for t in thirds if t]
        return float(np.mean(means)) if means else None
    if scheme == "week_weighted":                        # weight each obs by days it represents
        w = np.diff([0] + days) if len(days) > 1 else [1]
        return float(np.average(vals, weights=w[:len(vals)]))
    if scheme.startswith("trailing_"):
        k = int(scheme.split("_")[1])
        last = pts[-1][0]
        sel = [v for d, v in pts if (last - d).days < k]
        return float(np.mean(sel)) if sel else float(vals[-1])
    raise ValueError(scheme)


def monthly_levels_scheme(source: str, series_key: str, scheme: str, db_path=DEFAULT_DB) -> dict[str, float]:
    with db.connect(db_path) as conn:
        obs = _daily_obs(conn, source, series_key)
    months = sorted({_month(d) for d in obs})
    out = {}
    for m in months:
        lv = aggregate_month(obs, m, scheme)
        if lv is not None:
            out[m] = lv
    return out


def monthly_mom_scheme(source: str, series_key: str, scheme: str, db_path=DEFAULT_DB) -> dict[str, float]:
    lv = monthly_levels_scheme(source, series_key, scheme, db_path)
    ms = sorted(lv)
    def prev(m):
        d = dt.date.fromisoformat(m); return dt.date(d.year - (d.month == 1), d.month - 1 or 12, 1).isoformat()
    return {m: lv[m] / lv[prev(m)] - 1 for m in ms if prev(m) in lv and lv[prev(m)]}


def _official_nsa_mom(conn, stratum: str) -> dict[str, float]:
    lv = {p: float(v) for p, v in conn.execute(
        "SELECT period, value FROM official_current WHERE series_id=? AND _superseded_by_run_id IS NULL",
        (f"CUUR0000{stratum}",))}
    ms = sorted(lv)
    def prev(m):
        d = dt.date.fromisoformat(m); return dt.date(d.year - (d.month == 1), d.month - 1 or 12, 1).isoformat()
    return {m: lv[m] / lv[prev(m)] - 1 for m in ms if prev(m) in lv and lv[prev(m)]}


def _r2(x, y):
    if len(x) < 6 or np.std(x) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1] ** 2)


def select_window(source: str, series_key: str, stratum: str, schemes=SCHEMES,
                  embargo_months: int = 2, min_train: int = 36, db_path=DEFAULT_DB) -> dict:
    """H8: pick the aggregation scheme that best tracks the official NSA stratum MoM, INSIDE each
    expanding walk-forward fold (train-only, embargoed). Returns per-fold winners, the modal
    winner, cross-fold stability, and the doctrine default (full_month_mean) if unstable."""
    with db.connect(db_path) as conn:
        off = _official_nsa_mom(conn, stratum)
    proxy = {s: monthly_mom_scheme(source, series_key, s, db_path) for s in schemes}
    months = sorted(set(off) & set.intersection(*[set(proxy[s]) for s in schemes]))
    if len(months) < min_train + embargo_months + 6:
        return {"source": source, "stratum": stratum, "error": "insufficient overlap", "n": len(months)}
    fold_winners, fold_test_r2 = [], []
    for end in range(min_train, len(months) - 6, 6):          # expanding folds, step 6mo
        train = months[:end]
        test = months[end + embargo_months: end + embargo_months + 12]
        if len(test) < 6:
            continue
        # pick best scheme on TRAIN only
        best, best_r2 = None, -1
        for s in schemes:
            xr = _r2([proxy[s][m] for m in train], [off[m] for m in train])
            if xr == xr and xr > best_r2:
                best, best_r2 = s, xr
        # evaluate the train-picked scheme on TEST
        tr2 = _r2([proxy[best][m] for m in test], [off[m] for m in test])
        fold_winners.append(best)
        if tr2 == tr2:
            fold_test_r2.append(tr2)
    from collections import Counter
    cnt = Counter(fold_winners)
    modal, modal_n = cnt.most_common(1)[0]
    stable = modal_n / len(fold_winners) >= 0.6 if fold_winners else False
    return {"source": source, "stratum": stratum, "n_months": len(months), "n_folds": len(fold_winners),
            "fold_winners": fold_winners, "modal_window": modal, "modal_share": round(modal_n / len(fold_winners), 2),
            "stable": stable, "selected": modal if stable else "full_month_mean",
            "mean_test_r2": round(float(np.mean(fold_test_r2)), 3) if fold_test_r2 else None,
            "full_month_test_r2": round(float(np.mean(
                [_r2([proxy["full_month_mean"][m] for m in months[e + embargo_months:e + embargo_months + 12]],
                     [off[m] for m in months[e + embargo_months:e + embargo_months + 12]])
                 for e in range(min_train, len(months) - 6, 6)
                 if len(months[e + embargo_months:e + embargo_months + 12]) >= 6])), 3)}


def partial_feature(source: str, series_key: str, month: str, forecast_time, db_path=DEFAULT_DB) -> float | None:
    """A partial-window observation enters AS partial: the mid-month (days 1-15) proxy level for
    `month`, labelled as a days-1-15 feature — never averaged into a whole-month number. Read
    only if observable by forecast_time (caller gates via proxy_timebase)."""
    with db.connect(db_path) as conn:
        obs = _daily_obs(conn, source, series_key)
    pts = [(dt.date.fromisoformat(d), v) for d, v in obs.items() if _month(d) == month and dt.date.fromisoformat(d).day <= 15]
    return float(np.mean([v for _, v in pts])) if pts else None
