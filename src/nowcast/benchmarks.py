"""Benchmark evaluation — "vs the market's number" (Session 8).

Deterministic, offline. Reads three benchmark artifacts (data/benchmarks/*.csv) + our frozen calls
(docs/event_study_results.csv) + actuals/factors from the DB. No network, no refit, no config touch.

BASIS. The market variable is the SA MoM rounded to 0.1pp. Our instrument is NSA-native, so our call
is converted to the SA basis with a leakage-safe projected implied factor (prior-year same-month
NSA/SA), validated at ~2.5bp headline / ~1.9bp core — a stated handicap, not adjusted for. Rounded
(market) comparisons live in their own columns and are never blended with unrounded metrics.

The three PRE-REGISTERED claims (see checkpoint_log_s8.md) are consensus-specific:
  PR-1 side-of-consensus hit rate in divergence months (|call - consensus| >= 0.05pp)
  PR-2 boundary-month performance (rounded actual within 1.5bp of a 0.1pp boundary)
  PR-3 average MAE vs consensus (the handicap check; a surprise win triggers an audit)
They run the moment consensus_history is curated. `evaluate_against(benchmark=...)` runs the SAME
machinery against ANY benchmark, so PR-1/PR-3 can be previewed against the Cleveland Fed nowcast
(a real external number) while consensus is gap-first — clearly labelled as NOT the consensus test.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

import numpy as np

from nowcast import db

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "db" / "nowcast.sqlite"
BENCH = REPO / "data" / "benchmarks"
REPLAY = REPO / "docs" / "event_study_results.csv"
SA_ID = {"cpi_headline": "CUSR0000SA0", "cpi_core": "CUSR0000SA0L1E"}
NSA_ID = {"cpi_headline": "CUUR0000SA0", "cpi_core": "CUUR0000SA0L1E"}
ROUND = 0.1                      # market rounding unit, percentage points
BOUNDARY_BP = 1.5               # within 1.5bp of a 0.1pp boundary = COIN-FLIP / boundary month
DIVERGE_PP = 0.05               # half a rounding unit


def _add(m: str, k: int) -> str:
    d = dt.date.fromisoformat(m)
    mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def _levels(conn, sid: str) -> dict:
    return {p: float(v) for p, v in conn.execute(
        "SELECT period, value FROM official_current WHERE series_id=? AND _superseded_by_run_id IS NULL", (sid,))}


def actual_sa_mom_pct(conn, inst: str, ref: str) -> float | None:
    """Rounded market actual is derived from this: SA MoM in percentage points (unrounded)."""
    sa = _levels(conn, SA_ID[inst]); pm = _add(ref, -1)
    return (sa[ref] / sa[pm] - 1.0) * 100 if ref in sa and pm in sa and sa[pm] else None


def _proj_factor_ratio(conn, inst: str, ref: str) -> float | None:
    """Leakage-safe F_{t-1}/F_t using prior-year same-month implied NSA/SA factors."""
    nsa = _levels(conn, NSA_ID[inst]); sa = _levels(conn, SA_ID[inst])
    fy, fpy = _add(ref, -12), _add(_add(ref, -1), -12)
    F = {m: nsa[m] / sa[m] for m in (fy, fpy) if m in nsa and m in sa and sa[m]}
    return (F[fpy] / F[fy]) if fy in F and fpy in F else None


def our_call_sa_pct(conn, inst: str, ref: str, nsa_call_bp: float) -> float | None:
    """Convert our frozen NSA call (bp) to the SA basis (percentage points)."""
    r = _proj_factor_ratio(conn, inst, ref)
    return None if r is None else ((1 + nsa_call_bp / 10000) * r - 1) * 100


def our_calls() -> dict:
    """Our frozen T-3 NSA calls (bp) from the replay, keyed (instrument, ref_month)."""
    out = {}
    if not REPLAY.exists():
        return out
    for r in csv.DictReader(open(REPLAY)):
        out[(r["instrument"], r["ref_month"])] = float(r["call_bp"])
    return out


def load_cleveland() -> dict:
    """(series_key, ref_month) -> SA nowcast in pp."""
    p = BENCH / "cleveland_nowcast.csv"
    return {(r["series_key"], r["reference_month"]): float(r["value_pct_mom_sa"])
            for r in csv.DictReader(open(p))} if p.exists() else {}


def load_consensus() -> dict:
    """(mapped_instrument, ref_month) -> rounded consensus pp, curated rows only."""
    p = BENCH / "consensus_history.csv"
    if not p.exists():
        return {}
    vmap = {"mom_headline": "cpi_headline", "mom_core": "cpi_core"}
    out = {}
    for r in csv.DictReader(open(p)):
        if r["print"] == "CPI" and r["article_type"] in ("preview", "recap") and r["consensus_pct"]:
            k = vmap.get(r["variable"])
            if k:
                out[(k, r["reference_month"])] = float(r["consensus_pct"])
    return out


def _round(x: float) -> float:
    return round(x / ROUND) * ROUND


def evaluate_against(benchmark: str, instruments=("cpi_headline", "cpi_core")) -> dict:
    """Run PR-1 (side), PR-2 (boundary), PR-3 (MAE) machinery vs the named benchmark.
    benchmark in {"consensus", "cleveland"}. Returns per-instrument result dicts with n stated."""
    bench = load_consensus() if benchmark == "consensus" else load_cleveland()
    calls = our_calls()
    out = {"benchmark": benchmark, "instruments": {}}
    with db.connect(DB) as conn:
        for inst in instruments:
            rows = []
            for (i, ref), nsa_bp in calls.items():
                if i != inst:
                    continue
                b = bench.get((inst, ref))
                a = actual_sa_mom_pct(conn, inst, ref)
                ours = our_call_sa_pct(conn, inst, ref, nsa_bp)
                if b is None or a is None or ours is None:
                    continue
                ar = _round(a); br = _round(b)                     # rounded market variables
                boundary = abs((a / ROUND - round(a / ROUND))) * ROUND * 100 <= BOUNDARY_BP
                rows.append({"ref": ref, "actual_pp": a, "actual_round": ar, "ours_pp": ours,
                             "bench_round": br, "bench_pp": b, "boundary": boundary})
            out["instruments"][inst] = _summarize(rows)
    return out


def _summarize(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n": 0, "status": "no covered months"}
    # PR-3 MAE (rounded-actual basis for both; ours uses unrounded call vs rounded actual — noted)
    mae_ours = float(np.mean([abs(r["ours_pp"] - r["actual_pp"]) for r in rows])) * 100
    mae_bench = float(np.mean([abs(r["bench_pp"] - r["actual_pp"]) for r in rows])) * 100
    # PR-1 side-of-benchmark in divergence months (|ours - bench_round| >= 0.05pp), non-boundary
    div = [r for r in rows if abs(r["ours_pp"] - r["bench_round"]) >= DIVERGE_PP and not r["boundary"]]
    hits = sum(1 for r in div if np.sign(r["ours_pp"] - r["bench_round"]) ==
               np.sign(r["actual_pp"] - r["bench_round"]) and r["actual_pp"] != r["bench_round"])
    ties = sum(1 for r in div if r["actual_pp"] == r["bench_round"])
    # PR-2 boundary months
    bnd = [r for r in rows if r["boundary"]]
    err_ours_b = float(np.mean([abs(r["ours_pp"] - r["actual_pp"]) for r in bnd])) * 100 if bnd else None
    err_bench_b = float(np.mean([abs(r["bench_pp"] - r["actual_pp"]) for r in bnd])) * 100 if bnd else None
    return {
        "n": n,
        "PR3_mae_ours_bp": round(mae_ours, 2), "PR3_mae_bench_bp": round(mae_bench, 2),
        "PR1_divergence_n": len(div), "PR1_side_hits": hits, "PR1_ties": ties,
        "PR1_hit_rate": round(hits / (len(div) - ties), 3) if (len(div) - ties) else None,
        "PR1_binom_p": _binom_p(hits, len(div) - ties) if (len(div) - ties) else None,
        "PR2_boundary_n": len(bnd), "PR2_err_ours_bp": round(err_ours_b, 2) if bnd else None,
        "PR2_err_bench_bp": round(err_bench_b, 2) if bnd else None,
    }


def _binom_p(k: int, n: int) -> float:
    """Two-sided exact binomial p vs 0.5."""
    if n == 0:
        return float("nan")
    from math import comb
    pk = sum(comb(n, i) for i in range(n + 1) if abs(i - n / 2) >= abs(k - n / 2)) / 2 ** n
    return round(min(1.0, pk), 4)


def divergence_inventory(benchmark: str = "cleveland", inst: str = "cpi_headline") -> list[dict]:
    """Per-month table: our SA call, benchmark, rounded actual, divergence, side-correct."""
    bench = load_consensus() if benchmark == "consensus" else load_cleveland()
    calls = our_calls()
    rows = []
    with db.connect(DB) as conn:
        for (i, ref), nsa_bp in sorted(calls.items()):
            if i != inst:
                continue
            b = bench.get((inst, ref)); a = actual_sa_mom_pct(conn, inst, ref)
            ours = our_call_sa_pct(conn, inst, ref, nsa_bp)
            if b is None or a is None or ours is None:
                continue
            br = _round(b)
            rows.append({"ref": ref, "ours_pp": round(ours, 3), "bench_round": br,
                         "actual_round": _round(a), "actual_pp": round(a, 3),
                         "diverge_pp": round(ours - br, 3),
                         "diverges": abs(ours - br) >= DIVERGE_PP})
    return rows
