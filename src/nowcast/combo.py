"""H19 — forecast combination: `combo = w·ours + (1−w)·consensus`. **REPORTING LAYER ONLY.**

Standing labelling rule (binding): a combo number is **never** an accuracy claim about "ours". It is a
combination product, labelled `combo(ours,consensus)` wherever it appears. This module touches no
frozen config, no primary instrument, and no existing ledger row. If adopted, combo calls may join the
ledger as a **distinct instrument label** from the next freeze forward — never retrofitted.

Weight discipline (pre-registered): *w* is estimated on the **Cleveland panel, pre-2023 portion only**
— deliberately outside the consensus scoring window (2023+), so the weight is never fitted to the
months it is scored on. If the estimate is **unstable across folds** (sign flip, or spread > 0.25) the
pre-committed **w = 0.25** is used instead. Which path was taken is recorded per instrument.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
CSV = REPO / "data" / "benchmarks" / "backtest_vs_consensus.csv"
W_PRECOMMITTED = 0.25
UNSTABLE_SPREAD = 0.25
GRID = np.linspace(0.0, 1.0, 101)
INSTRUMENTS = ("cpi_headline", "cpi_core", "pce_core")


def _rows() -> list[dict]:
    return list(csv.DictReader(open(CSV)))


def _f(r, k):
    v = r.get(k, "")
    return float(v) if v not in ("", None) else None


def estimation_sample(inst: str, rows=None) -> list[dict]:
    """Pre-2023 months with our call + Cleveland + actual (Cleveland stands in for the survey)."""
    rows = rows or _rows()
    out = []
    for r in rows:
        if r["instrument"] != inst or r["reference_month"] >= "2023-01-01":
            continue
        o, c, a = _f(r, "our_call_pp"), _f(r, "cleveland_pp"), _f(r, "actual_pp")
        if None not in (o, c, a):
            out.append({"month": r["reference_month"], "ours": o, "other": c, "actual": a})
    return out


def scoring_sample(inst: str, rows=None) -> list[dict]:
    """Consensus months: our call + curated consensus + actual."""
    rows = rows or _rows()
    out = []
    for r in rows:
        if r["instrument"] != inst or not r["consensus_pp"]:
            continue
        o, c, a = _f(r, "our_call_pp"), _f(r, "consensus_pp"), _f(r, "actual_pp")
        if None not in (o, c, a):
            out.append({"month": r["reference_month"], "ours": o, "other": c, "actual": a})
    return out


def _best_w(sample: list[dict]) -> float:
    """w minimising MAE of the convex blend on `sample`."""
    ours = np.array([s["ours"] for s in sample])
    other = np.array([s["other"] for s in sample])
    act = np.array([s["actual"] for s in sample])
    mae = [np.abs(w * ours + (1 - w) * other - act).mean() for w in GRID]
    return float(GRID[int(np.argmin(mae))])


def choose_weight(inst: str, n_folds: int = 4, rows=None) -> dict:
    """Estimate w with a fold-stability check; fall back to the pre-committed weight if unstable.

    Returns the decision and its evidence, so the recorded reason is auditable either way.
    """
    est = estimation_sample(inst, rows)
    if len(est) < 12:
        return {"instrument": inst, "w": W_PRECOMMITTED, "path": "precommitted",
                "reason": f"estimation sample too small (n={len(est)}; needs >=12)",
                "n_est": len(est), "fold_ws": []}
    est = sorted(est, key=lambda s: s["month"])
    folds = np.array_split(np.arange(len(est)), n_folds)
    fold_ws = [_best_w([est[i] for i in idx]) for idx in folds if len(idx) >= 4]
    full_w = _best_w(est)
    spread = (max(fold_ws) - min(fold_ws)) if fold_ws else 1.0
    unstable = spread > UNSTABLE_SPREAD
    if unstable:
        return {"instrument": inst, "w": W_PRECOMMITTED, "path": "precommitted",
                "reason": f"fold-unstable: spread {spread:.2f} > {UNSTABLE_SPREAD}",
                "n_est": len(est), "fold_ws": fold_ws, "full_w": full_w, "spread": spread}
    return {"instrument": inst, "w": full_w, "path": "estimated",
            "reason": f"fold-stable: spread {spread:.2f} <= {UNSTABLE_SPREAD}",
            "n_est": len(est), "fold_ws": fold_ws, "full_w": full_w, "spread": spread}


def evaluate(inst: str, rows=None) -> dict:
    """Head-to-head on consensus months: ours vs consensus vs combo(ours,consensus). MAE in pp."""
    dec = choose_weight(inst, rows=rows)
    sc = scoring_sample(inst, rows)
    if not sc:
        return {**dec, "n_score": 0}
    w = dec["w"]
    ours = np.array([s["ours"] for s in sc])
    cons = np.array([s["other"] for s in sc])
    act = np.array([s["actual"] for s in sc])
    combo = w * ours + (1 - w) * cons
    return {**dec, "n_score": len(sc),
            "mae_ours_pp": round(float(np.abs(ours - act).mean()), 4),
            "mae_consensus_pp": round(float(np.abs(cons - act).mean()), 4),
            "mae_combo_pp": round(float(np.abs(combo - act).mean()), 4),
            "combo_vs_consensus_pp": round(float(np.abs(combo - act).mean()
                                                 - np.abs(cons - act).mean()), 4),
            "combo_vs_ours_pp": round(float(np.abs(combo - act).mean()
                                            - np.abs(ours - act).mean()), 4)}


def report() -> list[dict]:
    rows = _rows()
    return [evaluate(i, rows) for i in INSTRUMENTS]
