"""Event-study replay (Session 6, Task 1). Deterministic, offline. PURE REPLAY.

For every evaluable print in the OOS window: reconstruct the information set at the **T-3 freeze**
(timebase for official series, proxy_asof for proxies — both already enforced inside the frozen
models), run the FROZEN admitted configs (`config/component_models.yaml`, `pce_bridge` Instrument A),
and log call / benchmarks / realized first-release / deviation / attribution to a results table.

Nothing here re-fits, re-tunes, or regenerates a past call with today's information: the models
read only what `as_of` permits, and the configs are the admitted frozen ones. If the replay's
aggregate numbers disagree with `evaluation_1.md`, THAT IS THE FINDING (the freeze claim — that
nothing useful arrives after T-4 — is exactly what the comparison tests).
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

import numpy as np

from nowcast import component_models as CM
from nowcast import db, intramonth

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "db" / "nowcast.sqlite"
FREEZE_ASOF_DAYS = 3          # we stand at T-3; the model clamps to the T-4 freeze internally

TARGETS = {"cpi_headline": "CUUR0000SA0", "cpi_core": "CUUR0000SA0L1E"}


def _add(m, k):
    d = dt.date.fromisoformat(m); mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def _nsa_mom(conn, sid, m):
    px = {p: float(v) for p, v in conn.execute(
        "SELECT period, value FROM official_current WHERE series_id=? AND period IN (?,?) "
        "AND _superseded_by_run_id IS NULL", (sid, m, _add(m, -1)))}
    pm = _add(m, -1)
    return (px[m] / px[pm] - 1.0) if (m in px and pm in px and px[pm]) else None


def _seasonal_naive(conn, sid, m, years=8):
    xs = [_nsa_mom(conn, sid, _add(m, -12 * k)) for k in range(1, years + 1)]
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def evaluable_prints(start: str, end: str, db_path=DEFAULT_DB) -> list[str]:
    with db.connect(db_path) as conn:
        return [r[0] for r in conn.execute(
            "SELECT reference_period FROM release_calendar WHERE print='CPI' AND "
            "reference_period>=? AND reference_period<=? AND release_date<=? "
            "AND _superseded_by_run_id IS NULL ORDER BY reference_period", (start, end, dt.date.today().isoformat()))]


def replay_cpi(ref_month: str, instrument: str, cfg=None, db_path=DEFAULT_DB) -> dict | None:
    """Replay one CPI print at the T-3 freeze with the frozen admitted config."""
    sid = TARGETS[instrument]
    agg = "headline" if instrument.endswith("headline") else "core"
    with db.connect(db_path) as conn:
        rel = intramonth._release_date(conn, ref_month)
        if rel is None:
            return None
        realized = _nsa_mom(conn, sid, ref_month)
        bench_sn = _seasonal_naive(conn, sid, ref_month)
        bench_ar = _nsa_mom(conn, sid, _add(ref_month, -1))
    if realized is None:
        return None
    asof = rel - dt.timedelta(days=FREEZE_ASOF_DAYS)
    r = intramonth.nowcast_as_of(ref_month, asof, agg, db_path=db_path)
    call = r["forecast_mom"]
    if call is None:
        return None
    # attribution: the proxy-driven components' own calls (the part that is not the seasonal baseline)
    attrib = {}
    for code in (cfg or CM._cfg())["components"]:
        f = CM.forecast_component(code, ref_month, dt.date.fromisoformat(r["effective_asof"]), cfg, db_path)
        if f is not None:
            attrib[code] = round(f * 10000, 1)
    return {"instrument": instrument, "ref_month": ref_month, "release_date": rel.isoformat(),
            "asof": asof.isoformat(), "effective_asof": r["effective_asof"], "frozen": r["frozen"],
            "call_bp": round(call * 10000, 2), "realized_bp": round(realized * 10000, 2),
            "deviation_bp": round((call - realized) * 10000, 2),
            "bench_seasonal_naive_bp": round(bench_sn * 10000, 2) if bench_sn is not None else None,
            "bench_ar1_bp": round(bench_ar * 10000, 2) if bench_ar is not None else None,
            "bench_zero_bp": 0.0, "attribution": attrib}


def replay(start: str = "2019-01-01", end: str = "2026-12-01", instruments=("cpi_headline", "cpi_core"),
           db_path=DEFAULT_DB) -> list[dict]:
    cfg = CM._cfg()
    out = []
    for m in evaluable_prints(start, end, db_path):
        for inst in instruments:
            rec = replay_cpi(m, inst, cfg, db_path)
            if rec:
                out.append(rec)
    return out


def summarize(records: list[dict]) -> dict:
    out = {}
    for inst in sorted({r["instrument"] for r in records}):
        d = [abs(r["deviation_bp"]) for r in records if r["instrument"] == inst]
        sn = [abs(r["bench_seasonal_naive_bp"] - r["realized_bp"]) for r in records
              if r["instrument"] == inst and r["bench_seasonal_naive_bp"] is not None]
        ar = [abs(r["bench_ar1_bp"] - r["realized_bp"]) for r in records
              if r["instrument"] == inst and r["bench_ar1_bp"] is not None]
        out[inst] = {"n": len(d), "mae_bp": round(float(np.mean(d)), 2),
                     "bench_seasonal_naive_mae": round(float(np.mean(sn)), 2) if sn else None,
                     "bench_ar1_mae": round(float(np.mean(ar)), 2) if ar else None}
    return out


def write_results(records: list[dict], path=REPO / "docs" / "event_study_results.csv") -> Path:
    cols = ["instrument", "ref_month", "release_date", "asof", "effective_asof", "frozen",
            "call_bp", "realized_bp", "deviation_bp", "bench_seasonal_naive_bp", "bench_ar1_bp",
            "bench_zero_bp", "attribution"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            w.writerow({c: (r.get(c) if c != "attribution" else str(r.get(c))) for c in cols})
    return path
