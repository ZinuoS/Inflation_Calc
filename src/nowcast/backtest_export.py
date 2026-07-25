"""Backtest export — our call vs the actual release vs consensus, per print, **all in pp**.

Writes `data/benchmarks/backtest_vs_consensus.csv`: one row per (instrument, reference_month) with
our frozen call, the published actual, the press-consensus median, and the Cleveland Fed nowcast,
plus the three error columns. Percentage points throughout (the release convention; 1 pp = 100 bp).

    python -c "from nowcast import backtest_export as X; X.write_csv()"

BASIS DISCIPLINE (the thing that makes this comparison honest):
  * The market variable is **SA** MoM. CPI consensus figures are SA, so our **NSA-native** CPI call is
    converted to the SA basis with the leakage-safe prior-year implied factor
    (`benchmarks.our_call_sa_pct`, validated ~0.025 pp headline / ~0.019 pp core). That conversion is
    a **stated handicap on us**, never adjusted away — the `our_call_basis` column labels every row.
  * PCE Instrument A is natively SA, so no conversion applies (`native_sa`).
  * `actual_pp` is the unrounded SA MoM; `actual_rounded_pp` is the published tenth. Consensus is
    **already rounded** (it is a median of rounded forecasts) — so `consensus_err_pp` compares a
    rounded number to the unrounded actual and carries a small rounding penalty in consensus's favour
    or against it. Rounded and unrounded quantities are kept in separate columns and never averaged
    into one statistic.
  * Every consensus value carries its `consensus_source_url` + `consensus_article_date`, so each cell
    is traceable to the dated article it came from. Missing months are blank — gaps, never imputed.

No YoY column: hard rule 8 bars YoY as a target/metric (overlapping windows autocorrelate the error
series). YoY appears only as derived release context in `docs/pce_status_report.md`.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from nowcast import benchmarks as B
from nowcast import db

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "benchmarks" / "backtest_vs_consensus.csv"
CONSENSUS = REPO / "data" / "benchmarks" / "consensus_history.csv"
BOUNDARY_PP = 0.015          # COIN-FLIP: actual within 1.5 bp of a 0.1 pp boundary
INCREMENT_PP = 0.1

COLS = ["instrument", "reference_month", "release_date",
        "our_call_pp", "our_call_basis", "actual_pp", "actual_rounded_pp",
        "consensus_pp", "consensus_source_url", "consensus_article_date",
        "cleveland_pp", "our_err_pp", "consensus_err_pp", "cleveland_err_pp",
        "divergence_pp", "boundary_month", "notes"]


def _release_dates(print_name: str) -> dict:
    with db.connect(B.DB) as conn:
        return {r[0]: r[1] for r in conn.execute(
            "SELECT reference_period, release_date FROM release_calendar WHERE print=? "
            "AND _superseded_by_run_id IS NULL", (print_name,))}


def _consensus_meta() -> dict:
    """(instrument, ref_month) -> (pct, url, article_date) for curated rows only."""
    if not CONSENSUS.exists():
        return {}
    vmap = {("CPI", "mom_headline"): "cpi_headline", ("CPI", "mom_core"): "cpi_core",
            ("PCE", "mom_core"): "pce_core"}
    out = {}
    for r in csv.DictReader(open(CONSENSUS)):
        key = vmap.get((r["print"], r["variable"]))
        if key and r["article_type"] in ("preview", "recap") and r["consensus_pct"]:
            out[(key, r["reference_month"])] = (float(r["consensus_pct"]), r["source_url"],
                                                r["article_date"])
    return out


ND = 4          # published precision, pp. 0.0001 pp = 0.01 bp — finer than any release convention.


def _q(x):
    """Quantise to the published precision. Every derived column is computed FROM these quantised
    values, so the CSV is internally self-consistent: a reader recomputing
    `our_err_pp = our_call_pp - actual_pp` from the file gets exactly the printed number.
    (Formatting each column independently from full precision breaks that by up to 1e-3 pp.)"""
    return None if x is None else round(x, ND)


def _fmt(x, nd=ND):
    return "" if x is None else f"{x:+.{nd}f}"


def build_rows() -> list[dict]:
    calls = B.our_calls()
    cons = _consensus_meta()
    clev = B.load_cleveland()
    cpi_rel, pce_rel = _release_dates("CPI"), _release_dates("PCE")
    rows: list[dict] = []

    # ---- CPI: our NSA call -> SA basis, vs SA actual, vs (SA) consensus
    with db.connect(B.DB) as conn:
        for (inst, ref), nsa_bp in sorted(calls.items()):
            if inst not in ("cpi_headline", "cpi_core"):
                continue
            actual = B.actual_sa_mom_pct(conn, inst, ref)          # pp, unrounded SA
            ours = B.our_call_sa_pct(conn, inst, ref, nsa_bp)      # pp, SA-converted
            if actual is None or ours is None:
                continue
            c = cons.get((inst, ref))
            cl = clev.get((inst, ref))
            ours, actual, cl = _q(ours), _q(actual), _q(cl)
            cons_v = _q(c[0]) if c else None
            ar = round(actual / INCREMENT_PP) * INCREMENT_PP
            rows.append({
                "instrument": inst, "reference_month": ref, "release_date": cpi_rel.get(ref, ""),
                "our_call_pp": _fmt(ours), "our_call_basis": "sa_converted_from_nsa",
                "actual_pp": _fmt(actual), "actual_rounded_pp": f"{ar:+.1f}",
                "consensus_pp": f"{cons_v:+.1f}" if c else "",
                "consensus_source_url": c[1] if c else "", "consensus_article_date": c[2] if c else "",
                "cleveland_pp": _fmt(cl) if cl is not None else "",
                "our_err_pp": _fmt(_q(ours - actual)),
                "consensus_err_pp": _fmt(_q(cons_v - actual)) if c else "",
                "cleveland_err_pp": _fmt(_q(cl - actual)) if cl is not None else "",
                "divergence_pp": _fmt(_q(ours - cons_v)) if c else "",
                "boundary_month": "yes" if abs(actual - ar) <= BOUNDARY_PP else "no",
                "notes": "" if c else "consensus gap (not curated)",
            })

    # ---- PCE Instrument A: natively SA, no conversion
    from nowcast import pce_acceptance as PA
    acc = PA.evaluate("2023-01-01", "2026-05-01", "A")
    for mev in acc.months:
        ref = mev.ref_month
        ours, actual = _q(mev.bridge_bp / 100.0), _q(mev.actual_bp / 100.0)
        c = cons.get(("pce_core", ref))
        cl = _q(clev.get(("pce_core", ref)))
        cons_v = _q(c[0]) if c else None
        ar = round(actual / INCREMENT_PP) * INCREMENT_PP
        rows.append({
            "instrument": "pce_core", "reference_month": ref, "release_date": pce_rel.get(ref, ""),
            "our_call_pp": _fmt(ours), "our_call_basis": "native_sa",
            "actual_pp": _fmt(actual), "actual_rounded_pp": f"{ar:+.1f}",
            "consensus_pp": f"{cons_v:+.1f}" if c else "",
            "consensus_source_url": c[1] if c else "", "consensus_article_date": c[2] if c else "",
            "cleveland_pp": _fmt(cl) if cl is not None else "",
            "our_err_pp": _fmt(_q(ours - actual)),
            "consensus_err_pp": _fmt(_q(cons_v - actual)) if c else "",
            "cleveland_err_pp": _fmt(_q(cl - actual)) if cl is not None else "",
            "divergence_pp": _fmt(_q(ours - cons_v)) if c else "",
            "boundary_month": "yes" if abs(actual - ar) <= BOUNDARY_PP else "no",
            "notes": "" if c else "consensus gap (not curated)",
        })

    rows.sort(key=lambda r: (r["instrument"], r["reference_month"]))
    return rows


def write_csv(path: Path = OUT) -> Path:
    rows = build_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    return path


def summary(rows: list[dict] | None = None) -> dict:
    """Head-to-head MAE (pp) on the months where a consensus value exists — the only fair cut."""
    import numpy as np
    rows = rows or build_rows()
    out = {}
    for inst in ("cpi_headline", "cpi_core", "pce_core"):
        sub = [r for r in rows if r["instrument"] == inst and r["consensus_pp"]]
        if not sub:
            out[inst] = {"n": 0}
            continue
        ours = np.array([abs(float(r["our_err_pp"])) for r in sub])
        cons = np.array([abs(float(r["consensus_err_pp"])) for r in sub])
        out[inst] = {"n": len(sub), "our_mae_pp": round(float(ours.mean()), 4),
                     "consensus_mae_pp": round(float(cons.mean()), 4),
                     "boundary_months": sum(1 for r in sub if r["boundary_month"] == "yes")}
    return out
