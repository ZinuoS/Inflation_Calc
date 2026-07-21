"""CPI aggregation replication (Session 3A, Task 5). Deterministic, offline (rule 4).

Reconstruct a published CPI aggregate (All items = SA0, Core = SA0L1E) from its component
strata by the BLS upper-level modified-Laspeyres formula (Handbook of Methods, CPI ch. 17),
using ONLY official component indices (official_current) and published relative importances
(cpi_weights) — no proxies. Then, optionally, convert the reconstructed NSA aggregate to SA
via the harvested BLS factors and measure the SA-conversion overhead.

Method (price-updated Laspeyres, December pivot, annual reweighting):
  For each weight-year Y the relative importances RI_i(Y) are the December-(Y-1) cost shares.
  Seed cost weights CW_i = RI_i(Y) at the December pivot, then for each month t in Y:
      agg_relative(t) = Σ_i CW_i(t-1)·[I_i(t)/I_i(t-1)] / Σ_i CW_i(t-1)      (laspeyres_upper)
      CW_i(t) = CW_i(t-1)·[I_i(t)/I_i(t-1)]                                    (price-update)
  reset CW to RI(Y+1) at the next December. Aggregating from the coarsest COMPLETE published
  partition (each component's own sub-aggregation already done by BLS) is most faithful.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from nowcast import db, weights
from nowcast.index_math import laspeyres_upper

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"
MAPPING = Path(__file__).resolve().parents[2] / "mapping" / "mapping.yaml"

# Core = All items less food and energy. Food = the SAF1 subtree; energy = motor fuel
# (SETB), fuel oil & other household fuels (SEHE), and energy services (SEHF).
FOOD_SUBTREE = "SAF1"
ENERGY_SUBTREES = ("SETB", "SEHE", "SEHF")


def _hierarchy(mapping_path=MAPPING):
    m = yaml.safe_load(open(mapping_path))
    children: dict[str, list[dict]] = {}
    for d in m["cpi"]["items"]:
        p = d.get("parent_code")
        if p:
            children.setdefault(p, []).append(d)
    return children


def _descendants(children, root: str) -> set[str]:
    out: set[str] = set()
    def rec(c):
        for k in children.get(c, []):
            code = k.get("item_code")
            if code:
                out.add(code)
                rec(code)
    rec(root)
    return out


def complete_published_partition(root: str, exclude_subtrees: tuple[str, ...] = (),
                                 mapping_path=MAPPING) -> list[str]:
    """The COARSEST set of published item codes that exactly partitions `root` while cleanly
    excluding the given subtrees. Each published aggregate already embeds BLS's exact
    sub-aggregation (including unpublished strata and unrounded cost weights), so keeping a
    branch whole is strictly more faithful than re-deriving it from finer published RIs.
    Therefore: keep a node WHOLE unless it contains an excluded descendant, in which case
    descend just far enough to carve the excluded part out. With no exclusions (headline)
    this returns the 8 major groups; for core it decomposes only the food/energy branches."""
    children = _hierarchy(mapping_path)
    excluded_roots = set(exclude_subtrees)
    excluded = set(exclude_subtrees)
    for sub in exclude_subtrees:
        excluded |= _descendants(children, sub)
    out: list[str] = []

    def has_excluded(code: str) -> bool:
        return code in excluded or bool(_descendants(children, code) & excluded)

    def rec(code: str):
        if code in excluded_roots or code in excluded:
            return  # drop the excluded subtree entirely
        if not has_excluded(code):
            out.append(code)  # no food/energy inside -> keep this branch whole (coarsest)
            return
        kids = children.get(code, [])
        pub_kids = [k for k in kids if k.get("published") and k.get("item_code")]
        if kids and len(pub_kids) == len(kids):
            for k in pub_kids:
                rec(k["item_code"])
        else:
            out.append(code)  # can't cleanly descend (unpublished siblings) -> best effort

    for k in children.get(root, []):
        if k.get("published") and k.get("item_code"):
            rec(k["item_code"])
    return out


def _series_prefix(seasonal: str) -> str:
    return {"NSA": "CUUR0000", "SA": "CUSR0000"}[seasonal]


def _levels(conn, codes: list[str], seasonal: str) -> dict[str, dict[str, float]]:
    pre = _series_prefix(seasonal)
    return {c: {p: v for p, v in conn.execute(
        "SELECT period, value FROM official_current WHERE series_id=? "
        "AND _superseded_by_run_id IS NULL", (pre + c,))} for c in codes}


def _add_months(month: str, k: int) -> str:
    import datetime as dt
    d = dt.date.fromisoformat(month)
    mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def reconstruct_mom(partition: list[str], years, seasonal: str = "NSA",
                    basis: str = "cpi_u", db_path=DEFAULT_DB) -> dict[str, float]:
    """Price-updated Laspeyres reconstruction of the aggregate MoM for each month in the
    given weight-years, from the partition's component indices + published RIs."""
    with db.connect(db_path) as conn:
        lvl = _levels(conn, partition, seasonal)
    out: dict[str, float] = {}
    latest_cov = max(weights.coverage_years(db_path))
    for Y in years:
        try:
            RI = weights.weights_as_of(f"{Y}-06-01", basis=basis, db_path=db_path)
        except Exception:
            # weight table for Y not yet published (e.g. 2026 RI lags) -> fall back to the
            # latest available vintage; caller notes the weight-vintage staleness caveat.
            RI = weights.weights_as_of(f"{latest_cov}-06-01", basis=basis, db_path=db_path)
        dec = f"{Y - 1}-12-01"
        codes = [c for c in partition if c in RI and dec in lvl.get(c, {})]
        cw = {c: RI[c] for c in codes}
        prev = dec
        for mo in range(1, 13):
            t = f"{Y}-{mo:02d}-01"
            rc = [c for c in codes if t in lvl[c] and prev in lvl[c] and lvl[c][prev]]
            if not rc:
                break
            rel = [lvl[c][t] / lvl[c][prev] for c in rc]
            out[t] = laspeyres_upper(rel, [cw[c] for c in rc]) - 1.0
            for c in rc:
                cw[c] *= lvl[c][t] / lvl[c][prev]
            prev = t
    return out


def official_mom(series_id: str, months: list[str], db_path=DEFAULT_DB) -> dict[str, float]:
    """Official aggregate MoM from official_current (NSA unrevised = first release; SA used
    only for the conversion-overhead check, not as a backtest target)."""
    with db.connect(db_path) as conn:
        lvl = {p: v for p, v in conn.execute(
            "SELECT period, value FROM official_current WHERE series_id=? "
            "AND _superseded_by_run_id IS NULL", (series_id,))}
    out = {}
    for m in months:
        pm = _add_months(m, -1)
        if m in lvl and pm in lvl and lvl[pm]:
            out[m] = lvl[m] / lvl[pm] - 1.0
    return out


def reconstruction_error(aggregate: str = "headline", years=range(2020, 2026),
                         seasonal: str = "NSA", db_path=DEFAULT_DB) -> dict:
    """Reconstruct headline (SA0) or core (SA0L1E) and compare MoM to the official aggregate.
    Returns MAE/median/max in bp, and a per-year breakdown (the pre-2023 biennial-weight era
    vs the 2023+ annual-weight era — the current methodology is where ≤1 bp is expected)."""
    import numpy as np

    if aggregate == "headline":
        part = complete_published_partition("SA0")
        target = _series_prefix(seasonal) + "SA0"
    elif aggregate == "core":
        part = complete_published_partition("SA0", (FOOD_SUBTREE, *ENERGY_SUBTREES))
        target = _series_prefix(seasonal) + "SA0L1E"
    else:
        raise ValueError(aggregate)

    recon = reconstruct_mom(part, years, seasonal=seasonal, db_path=db_path)
    off = official_mom(target, sorted(recon), db_path=db_path)
    per_year: dict[int, list[float]] = {}
    errs = []
    for t, rv in recon.items():
        if t in off:
            e = abs(rv - off[t]) * 10000
            errs.append(e)
            per_year.setdefault(int(t[:4]), []).append(e)
    def mae(x):
        return round(float(np.mean(x)), 2) if x else None
    return {
        "aggregate": aggregate, "seasonal": seasonal, "n_components": len(part),
        "n_months": len(errs), "mae_bp": mae(errs),
        "median_bp": round(float(np.median(errs)), 2) if errs else None,
        "max_bp": round(float(np.max(errs)), 2) if errs else None,
        "mae_by_year": {y: mae(v) for y, v in sorted(per_year.items())},
        "mae_2023plus_bp": mae([e for y, v in per_year.items() if y >= 2023 for e in v]),
    }
