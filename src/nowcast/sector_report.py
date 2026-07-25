"""Sector-level backtest reporting (status report + nb06).

Measurement only: forecasts each leaf stratum at the **T-3 freeze** with the frozen admitted configs,
aggregates to the 8 CPI major groups, and compares to the official major-group NSA MoM. Nothing here
fits, tunes, or writes a config; it is the reporting layer behind `docs/status_report_0725.md` and
`notebooks/nb06_prediction_status.ipynb` (CLAUDE.md rule 1: notebooks import, they do not implement).

Deterministic and offline — reads `official_current` / `release_calendar` / committed CSV artifacts.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

import numpy as np
import yaml

from nowcast import component_models as CM
from nowcast import db, intramonth, weights

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "db" / "nowcast.sqlite"
REPLAY = REPO / "docs" / "event_study_results.csv"
FREEZE_DAYS = 3

MAJORS = {"SAF": "Food & beverages", "SAH": "Housing", "SAA": "Apparel",
          "SAT": "Transportation", "SAM": "Medical care", "SAR": "Recreation",
          "SAE": "Education & communication", "SAG": "Other goods & services"}


def _add(m: str, k: int) -> str:
    d = dt.date.fromisoformat(m)
    mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def _mapping():
    m = yaml.safe_load((REPO / "mapping" / "mapping.yaml").read_text())
    items = {d["item_code"]: d for d in m["cpi"]["items"] if d.get("item_code")}
    leaves = [d["item_code"] for d in m["cpi"]["items"]
              if d.get("is_stratum") and d.get("item_code")]
    return items, leaves


def _major_of(code: str, items: dict) -> str | None:
    cur = code
    for _ in range(14):
        if cur in MAJORS:
            return cur
        cur = items.get(cur, {}).get("parent_code")
        if not cur:
            return None
    return None


def sector_backtest(start: str = "2019-01-01", db_path=DEFAULT_DB) -> dict:
    """{ref_month: {major: {pred_bp, act_bp, err_bp, weight}}} at the T-3 freeze."""
    items, leaves = _mapping()
    grp = {c: _major_of(c, items) for c in leaves}
    cfg = CM._cfg()
    cov = weights.coverage_years(db_path)
    out: dict[str, dict] = {}
    with db.connect(db_path) as conn:
        months = [r[0] for r in conn.execute(
            "SELECT reference_period FROM release_calendar WHERE print='CPI' AND reference_period>=? "
            "AND release_date<=? AND _superseded_by_run_id IS NULL ORDER BY reference_period",
            (start, dt.date.today().isoformat()))]
        for mo in months:
            rel = intramonth._release_date(conn, mo)
            if rel is None:
                continue
            ft = rel - dt.timedelta(days=FREEZE_DAYS)
            yr = int(mo[:4])
            RI = weights.weights_as_of(f"{yr if yr in cov else max(cov)}-06-01", db_path=db_path)
            fc, wt = {}, {}
            for c in leaves:
                f = CM.forecast_component(c, mo, ft, cfg, db_path, conn=conn)
                w = RI.get(c, 0.0)
                if f is None or w <= 0:
                    continue
                fc[c], wt[c] = f, w
            rec = {}
            for g in MAJORS:
                sel = [c for c in fc if grp[c] == g]
                if not sel:
                    continue
                W = sum(wt[c] for c in sel)
                pred = sum(wt[c] * (1 + fc[c]) for c in sel) / W - 1
                px = {p: float(v) for p, v in conn.execute(
                    "SELECT period,value FROM official_current WHERE series_id=? AND period IN (?,?) "
                    "AND _superseded_by_run_id IS NULL", (f"CUUR0000{g}", mo, _add(mo, -1)))}
                pm = _add(mo, -1)
                if mo not in px or pm not in px or not px[pm]:
                    continue
                act = px[mo] / px[pm] - 1
                rec[g] = {"pred_bp": pred * 1e4, "act_bp": act * 1e4,
                          "err_bp": (pred - act) * 1e4, "weight": W}
            if rec:
                out[mo] = rec
    return out


def sector_stats(data: dict) -> list[dict]:
    """Per-sector MAE / bias / 80% empirical range, ranked by CPI weight share."""
    months = sorted(data)
    rows = []
    total_w = 0.0
    for g, name in MAJORS.items():
        e = np.array([data[m][g]["err_bp"] for m in months if g in data[m]])
        w = np.mean([data[m][g]["weight"] for m in months if g in data[m]]) if len(e) else 0.0
        if len(e) < 10:
            continue
        total_w += w
        rows.append({"sector": name, "code": g, "_w": w, "n": int(len(e)),
                     "mae_bp": float(np.abs(e).mean()), "bias_bp": float(e.mean()),
                     "p10_bp": float(np.percentile(e, 10)), "p90_bp": float(np.percentile(e, 90))})
    for r in rows:
        r["weight_share"] = r.pop("_w") / total_w if total_w else 0.0
    return sorted(rows, key=lambda r: -r["weight_share"])


def offset_series(data: dict) -> tuple[dict, dict]:
    """(gross, net) monthly series: gross = Σ|weighted sector contribution|, net = signed sum.

    The gap between them is the cancellation structure — the aggregate is more accurate than its
    parts because sector errors partly offset.
    """
    months = sorted(data)
    gross, net = [], []
    for m in months:
        tot = sum(data[m][g]["weight"] for g in data[m])
        cs = [(data[m][g]["weight"] / tot) * data[m][g]["err_bp"] for g in data[m]]
        gross.append(float(sum(abs(v) for v in cs)))
        net.append(float(sum(cs)))
    return ({"months": months, "values": gross}, {"months": months, "values": net})


def sector_contributions(data: dict) -> list[dict]:
    """Per-sector gross |contribution| and signed contribution to the aggregate error (bp)."""
    months = sorted(data)
    acc: dict[str, list[float]] = {g: [] for g in MAJORS}
    for m in months:
        tot = sum(data[m][g]["weight"] for g in data[m])
        for g in data[m]:
            acc[g].append((data[m][g]["weight"] / tot) * data[m][g]["err_bp"])
    out = [{"sector": MAJORS[g], "gross_bp": float(np.mean(np.abs(v))), "signed_bp": float(np.mean(v))}
           for g, v in acc.items() if v]
    return sorted(out, key=lambda r: -r["gross_bp"])


def aggregate_devs(instrument: str = "cpi_headline") -> np.ndarray:
    """Frozen-call deviations (bp). CPI from the Session-6 replay; PCE from the acceptance run."""
    if instrument.startswith("pce"):
        from nowcast import pce_acceptance as PA
        acc = PA.evaluate("2023-01-01", "2026-05-01", "A")
        return np.array([m.err_bp for m in acc.months])
    return np.array([float(r["deviation_bp"]) for r in csv.DictReader(open(REPLAY))
                     if r["instrument"] == instrument])
