"""H11 — sampling-aware seasonal fallback (Session 7, pre-registered in checkpoint_log_s7.md).

SHADOW EVALUATION ONLY. Nothing here edits `config/component_models.yaml`; the frozen baseline is
untouched unless and until Ash admits H11.

The frozen baseline (`component_models._seasonal_ar`) is uniform across strata:

    f_t = s_t + 0.3 * (y_{t-1} - s_{t-1}),    s_t = mean of trailing 8 same-calendar-month MoMs

`mapping/sampling.yaml` establishes (cited to the BLS Handbook of Methods) that the sampling design
is NOT uniform. H11 makes the deviation-carry design-conditional:

  * `housing_panel_6` (SEHA, SEHC01): the published change is a weighted average of 6-month rent
    ratios, one panel per month => a mechanically induced moving average. Longer AR memory should
    dominate a single lag.
  * `monthly_big3_bimonthly_elsewhere`: a shock outside NY/LA/Chicago enters over two consecutive
    prints => own-lag-1 carries signal. (This is the limb AS PRE-REGISTERED. The lag-2 reversal
    found at S3 is H11b and is deliberately NOT included here.)
  * `monthly_all_areas`: unchanged — the CONTROL. The design predicts no mechanism, so a gain here
    is a pre-registered RED FLAG, not a win.

Memory length k is swept as a CURVE, never tuned to a winner. AR coefficients are fitted by OLS on
TRAIN ONLY inside each fold of an expanding purged/embargoed walk-forward (embargo 2, min-train 48),
matching the harness used in `voc._walkforward`.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import yaml

from nowcast import db, weights

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "db" / "nowcast.sqlite"
SEASONAL_YEARS = 8          # frozen baseline value; H11 changes the CARRY, not the seasonal window
FROZEN_CARRY = 0.3          # the baseline's frozen AR(1) coefficient
MIN_TRAIN = 48
EMBARGO = 2
K_GRID = (1, 2, 3, 4, 6, 12)


def _add(m: str, k: int) -> str:
    d = dt.date.fromisoformat(m)
    mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def stratum_series(conn, stratum: str, start: str = "2005-01-01") -> tuple[list[str], np.ndarray]:
    """Months and NSA MoM for one stratum (first release == NSA, unrevised)."""
    lv = {p: float(v) for p, v in conn.execute(
        "SELECT period, value FROM official_current WHERE series_id=? AND _superseded_by_run_id IS NULL",
        (f"CUUR0000{stratum}",))}
    ms, ys = [], []
    for m in sorted(lv):
        if m < start:
            continue
        pm = _add(m, -1)
        if pm in lv and lv[pm]:
            ms.append(m)
            ys.append(lv[m] / lv[pm] - 1.0)
    return ms, np.asarray(ys)


def seasonal_and_deviation(months: list[str], y: np.ndarray, years: int = SEASONAL_YEARS):
    """Causal seasonal mean s_t (trailing same-calendar-month values only) and deviation y_t - s_t.

    s_t uses ONLY prior-year same-month observations, all of which are public before month t's
    print, so no future information enters.
    """
    idx = {m: i for i, m in enumerate(months)}
    s = np.full(len(y), np.nan)
    for i, m in enumerate(months):
        vals = [y[idx[_add(m, -12 * k)]] for k in range(1, years + 1) if _add(m, -12 * k) in idx]
        if vals:
            s[i] = float(np.mean(vals))
    return s, y - s


def _fit_predict_ar(d: np.ndarray, k: int, t: int) -> float | None:
    """OLS AR(k) on deviations, fitted on TRAIN ONLY (everything before t-EMBARGO), predicting t."""
    rows, tgt = [], []
    for i in range(k, t - EMBARGO):
        lags = d[i - k:i][::-1]
        if np.isnan(d[i]) or np.isnan(lags).any():
            continue
        rows.append(lags)
        tgt.append(d[i])
    if len(tgt) < MIN_TRAIN - EMBARGO:
        return None
    X = np.c_[np.ones(len(tgt)), np.asarray(rows)]
    yv = np.asarray(tgt)
    try:
        beta = np.linalg.lstsq(X, yv, rcond=None)[0]
    except np.linalg.LinAlgError:
        return None
    lags_t = d[t - k:t][::-1]
    if np.isnan(lags_t).any():
        return None
    return float(beta[0] + lags_t @ beta[1:])


def walkforward(months, y, k: int):
    """OOS forecasts for baseline and H11(k). Returns (idx, base_pred, h11_pred, actual)."""
    s, d = seasonal_and_deviation(months, y)
    out_i, base, h11 = [], [], []
    for t in range(MIN_TRAIN, len(y)):
        if np.isnan(s[t]) or np.isnan(y[t]):
            continue
        b = s[t] + (FROZEN_CARRY * d[t - 1] if t >= 1 and not np.isnan(d[t - 1]) else 0.0)
        p = _fit_predict_ar(d, k, t)
        if p is None:
            continue
        out_i.append(t)
        base.append(b)
        h11.append(s[t] + p)
    i = np.asarray(out_i, dtype=int)
    return i, np.asarray(base), np.asarray(h11), y[i] if len(i) else np.asarray([])


def evaluate_stratum(conn, stratum: str, k: int) -> dict | None:
    months, y = stratum_series(conn, stratum)
    if len(y) < MIN_TRAIN + 24:
        return None
    i, base, h11, act = walkforward(months, y, k)
    if len(i) < 24:
        return None
    return {"stratum": stratum, "k": k, "n": len(i),
            "mae_base_bp": float(np.mean(np.abs(base - act))) * 10000,
            "mae_h11_bp": float(np.mean(np.abs(h11 - act))) * 10000,
            "months": [months[j] for j in i],
            "delta_forecast": h11 - base}


def sampling_classes() -> dict[str, str]:
    s = yaml.safe_load((REPO / "mapping" / "sampling.yaml").read_text())["strata"]
    return {c: v["collection_frequency"] for c, v in s.items()}


def run(k_grid=K_GRID, db_path=DEFAULT_DB) -> dict:
    """Full H11 sweep across every stratum, grouped by CITED collection design."""
    classes = sampling_classes()
    res: dict[int, list[dict]] = {}
    with db.connect(db_path) as conn:
        for k in k_grid:
            rows = []
            for code in classes:
                r = evaluate_stratum(conn, code, k)
                if r:
                    r["design"] = classes[code]
                    rows.append(r)
            res[k] = rows
    return res


def headline_delta(rows: list[dict], applies: set[str], db_path=DEFAULT_DB) -> dict:
    """Weighted headline effect of applying H11 to `applies` strata only.

    Returns per-month change in the aggregate forecast (bp). H11 changes only non-proxy strata, so
    the aggregate difference is the RI-weighted sum of per-stratum forecast changes.
    """
    m = yaml.safe_load((REPO / "mapping" / "mapping.yaml").read_text())
    leaves = [d["item_code"] for d in m["cpi"]["items"] if d.get("is_stratum") and d.get("item_code")]
    cov = weights.coverage_years(db_path)
    per_month: dict[str, float] = {}
    for r in rows:
        if r["stratum"] not in applies:
            continue
        for mo, dlt in zip(r["months"], r["delta_forecast"]):
            yr = int(mo[:4])
            RI = weights.weights_as_of(f"{yr if yr in cov else max(cov)}-06-01", db_path=db_path)
            tot = sum(RI.get(c, 0.0) for c in leaves)
            w = RI.get(r["stratum"], 0.0)
            if w > 0 and tot > 0:
                per_month[mo] = per_month.get(mo, 0.0) + (w / tot) * dlt * 10000
    return per_month
