"""Structured per-component nowcast models (Session 4, Task 2). Deterministic, offline.

The PRIMARY forecast layer: predict each CPI stratum's first-release NSA MoM *before* BLS prints
it, then aggregate. Boring by design — economics-imposed pass-through where a proxy pins the
price (gasoline), a leading-proxy feature where one exists (Manheim→used cars, lag-2), and a
seasonal baseline everywhere else (NSA MoM is dominated by its seasonal pattern). Configs are
frozen in config/component_models.yaml.

Firewall discipline: proxy reads are gated to obs publishable by `forecast_time` (proxy_timebase)
and aggregated by the H8-selected within-month window (windows.py); the stratum's own NSA history
uses only months already printed at forecast_time (NSA is unrevised = first-release). No look-ahead.
DEGRADED feature set: no Keepa daily goods panel — annotate downstream.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import yaml

from nowcast import db, index_math, weights, windows
from nowcast import proxy_timebase as PT

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "db" / "nowcast.sqlite"
CONFIG = REPO / "config" / "component_models.yaml"


def _cfg():
    return yaml.safe_load(open(CONFIG))


def _add_months(m: str, k: int) -> str:
    d = dt.date.fromisoformat(m); mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def _ft_date(forecast_time) -> dt.date:
    return forecast_time if isinstance(forecast_time, dt.date) else dt.date.fromisoformat(str(forecast_time)[:10])


def _proxy_month_mom(source, series_key, ref_month, window, forecast_time, db_path) -> float | None:
    """The proxy's within-month-windowed MoM for ref_month, using ONLY daily obs publishable by
    forecast_time (proxy_timebase.observed_asof). Vintage-safe."""
    ft = _ft_date(forecast_time)
    with db.connect(db_path) as conn:
        obs = windows._daily_obs(conn, source, series_key)
    pub = {d: v for d, v in obs.items() if PT.observed_asof(source, d) <= ft}
    lm = windows.aggregate_month(pub, ref_month, window)
    lp = windows.aggregate_month(pub, _add_months(ref_month, -1), window)
    return lm / lp - 1.0 if (lm and lp) else None


def _seasonal_ar(conn, stratum: str, ref_month: str, forecast_time, years: int, ar_lags: int) -> float | None:
    """Baseline: mean of the trailing `years` same-calendar-month NSA MoMs (the seasonal shape),
    plus a small AR(1) carry of last printed month's deviation from its own seasonal mean. Uses
    only months whose print is public at forecast_time (NSA unrevised = first release)."""
    lv = {p: float(v) for p, v in conn.execute(
        "SELECT period, value FROM official_current WHERE series_id=? AND _superseded_by_run_id IS NULL",
        (f"CUUR0000{stratum}",))}
    def mom(m):
        pm = _add_months(m, -1)
        return lv[m] / lv[pm] - 1.0 if (m in lv and pm in lv and lv[pm]) else None
    # last printed reference month = ref_month - 1 (its CPI is out by forecast_time)
    last = _add_months(ref_month, -1)
    same = [mom(_add_months(ref_month, -12 * k)) for k in range(1, years + 1)]
    same = [x for x in same if x is not None]
    if not same:
        return None
    seasonal = float(np.mean(same))
    if ar_lags and mom(last) is not None:
        # last month's deviation from ITS seasonal mean, carried at 0.3 (boring, frozen)
        lsame = [mom(_add_months(last, -12 * k)) for k in range(1, years + 1)]
        lsame = [x for x in lsame if x is not None]
        if lsame:
            seasonal += 0.3 * (mom(last) - float(np.mean(lsame)))
    return seasonal


def forecast_component(stratum: str, ref_month: str, forecast_time, cfg=None, db_path=DEFAULT_DB,
                       conn=None) -> float | None:
    """Predicted first-release NSA MoM for one stratum at forecast_time. Pass `conn` to reuse one
    connection across a batch (the aggregate call does this)."""
    cfg = cfg or _cfg()
    c = cfg["components"].get(stratum)
    if c and c["model"] == "pass_through":
        p = c["proxy"]
        pm = _proxy_month_mom(p["source"], p["series_key"], ref_month, p["window"], forecast_time, db_path)
        return None if pm is None else c["intercept"] + c["beta"] * pm
    if c and c["model"] == "lead_feature":
        p = c["proxy"]
        pm = _proxy_month_mom(p["source"], p["series_key"], _add_months(ref_month, -p["lead"]),
                              p["window"], forecast_time, db_path)
        return None if pm is None else c["intercept"] + c["beta"] * pm
    d = cfg["default"]
    if conn is not None:
        return _seasonal_ar(conn, stratum, ref_month, forecast_time, d["seasonal_years"], d.get("ar_lags", 1))
    with db.connect(db_path) as _c:
        return _seasonal_ar(_c, stratum, ref_month, forecast_time, d["seasonal_years"], d.get("ar_lags", 1))


def forecast_aggregate_nsa(ref_month: str, forecast_time, aggregate: str = "headline",
                           cfg=None, db_path=DEFAULT_DB) -> dict:
    """Nowcast the aggregate first-release NSA MoM: forecast each partition stratum, Laspeyres-
    aggregate with the vintage-appropriate weights. Returns the forecast + how many components
    used a proxy vs the seasonal baseline (the honest 'how much is signal vs baseline')."""
    import yaml as _yaml
    cfg = cfg or _cfg()
    # Forecast at the LEAF-stratum level so the stratum proxies (gasoline SETB01, used cars
    # SETA02) actually apply; everything else falls to the seasonal baseline. Core excludes the
    # food (SAF1) and energy (SETB/SEHE/SEHF) leaves.
    m = _yaml.safe_load(open(REPO / "mapping" / "mapping.yaml"))
    items = {d["item_code"]: d for d in m["cpi"]["items"] if d.get("item_code")}
    def _anc(code, roots):
        cur = code
        for _ in range(12):
            if cur in roots:
                return True
            cur = items.get(cur, {}).get("parent_code")
            if not cur:
                return False
        return False
    leaves = [d["item_code"] for d in m["cpi"]["items"] if d.get("is_stratum") and d.get("item_code")]
    if aggregate == "core":
        leaves = [c for c in leaves if not _anc(c, {"SAF1", "SETB", "SEHE", "SEHF"})]
    part = leaves
    yr = int(ref_month[:4])
    RI = weights.weights_as_of(f"{yr}-06-01", db_path=db_path) if yr in weights.coverage_years(db_path) \
        else weights.weights_as_of(f"{max(weights.coverage_years(db_path))}-06-01", db_path=db_path)
    rels, ws, n_proxy = [], [], 0
    with db.connect(db_path) as _conn:
        for code in part:
            f = forecast_component(code, ref_month, forecast_time, cfg, db_path, conn=_conn)
            w = RI.get(code, 0.0)
            if f is None or w <= 0:
                continue
            if code in cfg["components"]:
                n_proxy += 1
            rels.append(1.0 + f); ws.append(w)
    if not rels:
        return {"forecast_mom": None}
    agg = index_math.laspeyres_upper(rels, ws) - 1.0
    proxy_wt = sum(RI.get(c, 0.0) for c in part if c in cfg["components"]) / sum(ws)
    return {"aggregate": aggregate, "ref_month": ref_month, "forecast_mom": agg,
            "n_components": len(rels), "n_proxy_driven": n_proxy,
            "proxy_weight_share": round(proxy_wt, 4), "degraded_feature_set": "no_keepa_goods_panel"}
