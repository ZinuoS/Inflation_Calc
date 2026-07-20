"""Reconciliation harness (Session 2B, Task 3). Deterministic, offline (rule 4).

For each (proxy, official component) pair: regress OFFICIAL first-release MoM on the
aligned PROXY MoM over the full overlap; report beta, R², and 3-year rolling-window
stability. A pair is UNSTABLE if beta sign flips across rolling windows OR R²
collapses in the 2021-22 or 2025-26 stress windows.

Amendment 2 (binding):
  * Official MoM is read ONLY via timebase.asof_mom_for_ref (first-release,
    within-vintage) -- never a latest-vintage view. Shutdown-gap / series-start
    reference months raise NoMomExists and are counted in skipped_months, never
    imputed.
  * Any stat computed from a revised_latest_only proxy is annotated
    "optimistic: proxy vintage unavailable" -- the proxy's own history has been
    restated, so its real-time tracking is necessarily better here than it was live.

This table decides Session-4 feature admission. Flagged, never silently dropped.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

import numpy as np

from nowcast import alignment
from nowcast.timebase import NoMomExists, NotYetReleased, PreVintageFloor, open_timebase

ET = ZoneInfo("America/New_York")
STRESS_WINDOWS = (("2021-01-01", "2022-12-31"), ("2025-01-01", "2026-12-31"))
WINDOW_MONTHS = 36
R2_COLLAPSE = 0.10
OPTIMISM_NOTE = "optimistic: proxy vintage unavailable"


@dataclass
class Pair:
    proxy_source: str
    proxy_series_key: str
    official_series: str
    label: str
    cpi_weight: float
    proxy_vintage_status: str
    note: str = ""
    is_monitor: bool = False


@dataclass
class Result:
    label: str
    cpi_weight: float
    n_overlap: int
    skipped_months: int
    pre_floor_months: int = 0
    beta: float | None = None
    r2: float | None = None
    rolling_betas: list[float] = field(default_factory=list)
    stress_r2: dict[str, float] = field(default_factory=dict)
    proxy_quality: str = ""
    optimistic: bool = False
    note: str = ""


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Return (beta, R2) for y ~ a + b x. R2 is the squared Pearson correlation."""
    if len(x) < 3 or np.std(x) == 0:
        return float("nan"), float("nan")
    beta = float(np.polyfit(x, y, 1)[0])
    r = float(np.corrcoef(x, y)[0, 1])
    return beta, r * r


def _official_mom(tb, series: str, months: list[str], forecast_time) -> tuple[dict[str, float], int, int]:
    """First-release within-vintage official MoM per month via the sanctioned path.
    Returns (mom_by_month, skipped_months, pre_floor_months)."""
    out: dict[str, float] = {}
    skipped = 0
    pre_floor = 0
    for m in months:
        try:
            out[m] = tb.asof_mom_for_ref(series, m, forecast_time)
        except PreVintageFloor:
            pre_floor += 1  # restated-as-first -- excluded by construction, counted
        except NoMomExists:
            skipped += 1  # series-start or shutdown gap -- never imputed
        except NotYetReleased:
            skipped += 1  # not public yet at forecast_time
    return out, skipped, pre_floor


def reconcile_pair(db_path, tb, pair: Pair, forecast_time) -> Result:
    if pair.is_monitor:
        levels = alignment.monthly_levels(db_path, pair.proxy_source, pair.proxy_series_key)
        return Result(
            label=pair.label, cpi_weight=pair.cpi_weight, n_overlap=len(levels),
            skipped_months=0, proxy_quality="monitor",
            optimistic=(pair.proxy_vintage_status == "revised_latest_only"),
            note=pair.note + " | MONITOR: wage-growth rate, not regressed as a price proxy",
        )

    proxy_mom = alignment.monthly_mom(db_path, pair.proxy_source, pair.proxy_series_key)
    official_mom, skipped, pre_floor = _official_mom(
        tb, pair.official_series, sorted(proxy_mom), forecast_time
    )
    common = sorted(set(proxy_mom) & set(official_mom))
    res = Result(label=pair.label, cpi_weight=pair.cpi_weight, n_overlap=len(common),
                 skipped_months=skipped, pre_floor_months=pre_floor, note=pair.note,
                 optimistic=(pair.proxy_vintage_status == "revised_latest_only"))
    if len(common) < WINDOW_MONTHS:
        res.proxy_quality = "insufficient_overlap"
        return res

    x = np.array([proxy_mom[m] for m in common])
    y = np.array([official_mom[m] for m in common])
    res.beta, res.r2 = _ols(x, y)

    # rolling 36-month windows (step 12) for stability
    for start in range(0, len(common) - WINDOW_MONTHS + 1, 12):
        wx, wy = x[start:start + WINDOW_MONTHS], y[start:start + WINDOW_MONTHS]
        b, r2 = _ols(wx, wy)
        if not np.isnan(b):
            res.rolling_betas.append(round(b, 4))
        # record R2 for windows overlapping a stress period
        wmonths = common[start:start + WINDOW_MONTHS]
        for lo, hi in STRESS_WINDOWS:
            if any(lo <= m <= hi for m in wmonths) and not np.isnan(r2):
                res.stress_r2[f"{wmonths[0]}..{wmonths[-1]}"] = round(r2, 3)

    sign_flip = res.rolling_betas and (min(res.rolling_betas) < 0 < max(res.rolling_betas))
    stress_collapse = any(v < R2_COLLAPSE for v in res.stress_r2.values())
    if sign_flip or stress_collapse:
        res.proxy_quality = "unstable"
    elif res.r2 is not None and res.r2 < R2_COLLAPSE:
        res.proxy_quality = "weak"
    else:
        res.proxy_quality = "stable"
    return res


def build_pairs(mapping_path) -> list[Pair]:
    """The Session-2B (proxy, official) pairs that have data on both sides.
    Weights pulled from mapping.yaml. Availability/granularity caveats in `note`."""
    import yaml

    m = yaml.safe_load(open(mapping_path))
    w = {d["item_code"]: d["weight_cpi_u"] for d in m["cpi"]["items"] if d.get("item_code")}
    return [
        Pair("zori", "US", "CUSR0000SEHA", "ZORI vs CPI Rent of primary residence",
             w.get("SEHA", 7.84), "revised_latest_only",
             "SA vs SA; primary shelter pair. ZORI is a market-rent index; CPI rent is a "
             "smoothed all-tenant series lagging market by ~1yr (research plan H2)."),
        Pair("zori", "US", "CUSR0000SAH1", "ZORI vs CPI Shelter (SAH1)",
             w.get("SAH1", 0.0), "revised_latest_only", "coarser: shelter incl OER + lodging"),
        Pair("eia_gasoline", "US", "CUSR0000SETB01", "EIA gasoline vs CPI Gasoline (SETB01)",
             w.get("SETB01", 2.895), "unrevised",
             "stratum-level (Session-2B add); beta ~pass-through. NSA proxy vs SA official "
             "caps R² (SA is Session 3A); ALFRED first-release from ~2011."),
        Pair("zori", "US", "CUSR0000SEHC01", "ZORI vs CPI OER (SEHC01)",
             w.get("SEHC01", 25.23), "revised_latest_only",
             "OER direct (Session-2B add, 25% weight). H2 again: R²~0, unstable — market "
             "rent leads all-tenant OER ~1yr; ALFRED first-release from ~2011."),
        Pair("eia_heating_oil", "US_NYH_SPOT", "CPIENGSL", "EIA heating-oil spot vs CPI Energy",
             w.get("SEHE01", 0.083), "unrevised", "VERY COARSE: wholesale spot vs energy aggregate"),
        Pair("nadac", "US_drug_index", "CUSR0000SAM1", "NADAC vs CPI Medical-care commodities",
             w.get("SEMF01", 0.973), "unrevised",
             "PLACEHOLDER index, 1-year bounded (2024-25) -> too short for the rolling "
             "harness (insufficient_overlap expected). Official side = SAM1 (medical-care "
             "commodities) since drugs stratum SEMF01 has no ALFRED vintages. 3A: full "
             "history + proper weighted matched-model + drug-specific official."),
        Pair("atlanta_fed_wage", "US_overall_median", "", "Atlanta Fed wage tracker",
             0.0, "revised_latest_only", "", True),
        Pair("indeed_wage", "US_posted_wage_growth_yoy", "", "Indeed wage tracker",
             0.0, "revised_latest_only", "", True),
    ]


def run(db_path, pairs: list[Pair], forecast_time=None) -> list[Result]:
    forecast_time = forecast_time or dt.datetime.now(ET)
    results = []
    with open_timebase(db_path) as tb:
        for pair in pairs:
            results.append(reconcile_pair(db_path, tb, pair, forecast_time))
    # sort by CPI weight x R2 (monitors / no-R2 sink to the bottom)
    results.sort(key=lambda r: (r.cpi_weight * (r.r2 or 0.0)), reverse=True)
    return results


def _fmt(v, spec="+.3f"):
    return format(v, spec) if isinstance(v, float) and v == v else "—"


def write_report(results: list[Result], path) -> None:
    """docs/reconciliation_report.md: table sorted by weight×R², UNSTABLE list with
    one-line diagnoses, and the optimism-flagged count (Amendment 2)."""
    unstable = [r for r in results if r.proxy_quality == "unstable"]
    optimistic = [r for r in results if r.optimistic]
    lines = [
        "# Reconciliation report (Session 2B, Gate 2)",
        "",
        "Official-side MoM read via `timebase.asof_mom_for_ref` (first-release, within-vintage) "
        "— never latest-vintage. Shutdown/series-start months are counted in `skipped`, never imputed. "
        "`optimistic` marks stats from `revised_latest_only` proxies (their history was restated, so "
        "real-time tracking is necessarily flattered here).",
        "",
        "## Table (sorted by CPI weight × R²)",
        "",
        "`pre_floor` = official reference months excluded for being below the series' "
        "vintage_floor (ALFRED bulk-archived, restated-as-first). `skip` = shutdown-gap / "
        "series-start / not-yet-released. Both excluded from the regression, never imputed.",
        "",
        "| pair | CPI wt | n | skip | pre_floor | beta | R² | quality | optimistic |",
        "|---|--:|--:|--:|--:|--:|--:|---|:--:|",
    ]
    for r in results:
        lines.append(
            f"| {r.label} | {r.cpi_weight:.2f} | {r.n_overlap} | {r.skipped_months} | "
            f"{r.pre_floor_months} | {_fmt(r.beta)} | {_fmt(r.r2, '.3f')} | {r.proxy_quality} | "
            f"{'✓' if r.optimistic else ''} |"
        )
    lines += ["", f"**Optimism-flagged pairs (proxy vintage unavailable): {len(optimistic)}**", ""]
    lines += ["## UNSTABLE pairs — one-line diagnoses", ""]
    for r in unstable:
        flips = r.rolling_betas and (min(r.rolling_betas) < 0 < max(r.rolling_betas))
        collapse = [k for k, v in r.stress_r2.items() if v < R2_COLLAPSE]
        why = []
        if flips:
            why.append(f"beta sign flips across windows ({min(r.rolling_betas):+.2f}..{max(r.rolling_betas):+.2f})")
        if collapse:
            why.append(f"R² collapses in stress window(s) {collapse}")
        lines.append(f"- **{r.label}** (R²={_fmt(r.r2, '.3f')}): " + "; ".join(why) + f". {r.note}")
    lines += ["", "## Monitors (not regressed)", ""]
    for r in results:
        if r.proxy_quality == "monitor":
            lines.append(f"- **{r.label}**: {r.note}")
    lines.append("")
    open(path, "w").write("\n".join(lines))


def write_mapping_quality(results: list[Result], mapping_path) -> None:
    """Write proxy_quality + vintage-optimism back into mapping.yaml under a
    top-level `reconciliation` key (flagged, never dropped). Also stamps
    proxy_quality onto matching alt entries for the primary (first) pair per proxy."""
    import yaml

    m = yaml.safe_load(open(mapping_path))
    m["reconciliation"] = {
        "note": "Session 2B Gate 2. quality: stable|weak|unstable|monitor|insufficient_overlap. "
                "optimistic=stat from revised_latest_only proxy.",
        "pairs": [
            {"label": r.label, "cpi_weight": r.cpi_weight, "n_overlap": r.n_overlap,
             "skipped_months": r.skipped_months,
             "beta": round(r.beta, 4) if isinstance(r.beta, float) and r.beta == r.beta else None,
             "r2": round(r.r2, 4) if isinstance(r.r2, float) and r.r2 == r.r2 else None,
             "proxy_quality": r.proxy_quality, "optimistic": r.optimistic}
            for r in results
        ],
    }
    with open(mapping_path, "w") as f:
        f.write("# mapping.yaml — generated by Session-1 Task-2 generator; alt rows updated by Session-2B ingest.\n")
        f.write("# Edit alt/bridge rows by hand; CPI hierarchy+weights regenerate from raw pull.\n")
        yaml.safe_dump(m, f, sort_keys=False, allow_unicode=True, width=110)
