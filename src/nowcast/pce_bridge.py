"""CPI/PPI -> core-PCE bridge (Session 3B). Deterministic, offline (rule 4).

The bridge runs POST-CPI+PPI release for a reference month: it assembles unrounded core
PCE MoM from the just-released official CPI/PPI component price changes, weighted by PCE
expenditure shares. It does NOT forecast SA (Session 4) and does NOT re-estimate seasonal
factors — it reads first-release published SA components through `timebase` where those
components are ALFRED-vintaged, and falls back to `official_current` (latest published) with
an explicit `latest_vintage` optimism flag where they are not (flagged, never hidden — the
mirror of reconcile.py's optimism flag).

Assembly (BEA NIPA chain-Fisher, Handbook "Concepts and Methods of the U.S. NIPAs"):
  core PCE relative(t) = weighted combination of component price relatives with PCE weights.
  A true chain-Fisher needs BOTH periods' nominal expenditures (BEA underlying detail,
  Table 2.4.5U); with a single weight vintage we compute the Laspeyres leg — a documented
  approximation that collapses to Fisher for small monthly changes. `index_math.fisher` is
  used where both-period nominal weights are available (bea_pce_detail), else Laspeyres.

DATA-READINESS (Session-3B Task 0/1 findings — surfaced at CHECKPOINT 1, not hidden):
  * PCE WEIGHTS: intended source bea_pce_detail (Table 2.4.5U) is BEA-API-key-blocked and not
    publicly downloadable without the key (robots/JS-gated). `pce_weights` therefore reads
    bea_pce_detail if present, else (allow_approximate) returns CPI-relative-importance-derived
    proxy weights, loudly flagged. Real gate needs BEA.
  * FIRST-RELEASE VINTAGES: only SEHA, SEHC, SETA01, SETA02, SETB01 (rent/OER/vehicles/gas)
    are ALFRED-vintaged; the other ~45 CPI and all PPI feeders read latest-vintage (flagged).
  * S&P-500 PATH: portfolio_management (PPI discontinued 2022-12) and
    financial_services_without_payment need an S&P-500 path not yet ingested -> APPROXIMATED.
  * ATTRIBUTION: bea_pce_detail price table (2.4.4U) blocked -> component attribution of PCE
    misses is degraded (Task 0).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from nowcast import db, weights
from nowcast.timebase import NoMomExists, NotYetReleased, PreVintageFloor, UnknownSeries

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"
MAPPING = Path(__file__).resolve().parents[2] / "mapping" / "mapping.yaml"

# Portfolio-management PPI discontinued 2022-12 (mapping.yaml absence note); post-2022 the
# mapping prescribes an S&P-500 path. Frozen boundary.
PORTFOLIO_PPI_DISCONTINUED = "2022-12-01"


def _vintaged_series(conn) -> set[str]:
    """Series with genuine ALFRED first-release vintages (a MoM in first_release_mom) — read
    vintage-correct via timebase. Detected dynamically so newly-ingested feeders count."""
    return {r[0] for r in conn.execute("SELECT DISTINCT series_id FROM first_release_mom")}


def _has_series(conn, sid: str) -> bool:
    return conn.execute("SELECT 1 FROM official_current WHERE series_id=? AND _superseded_by_run_id IS NULL LIMIT 1",
                        (sid,)).fetchone() is not None


def _has_proxy(conn, source: str) -> bool:
    return conn.execute("SELECT 1 FROM proxy_observations WHERE source=? LIMIT 1", (source,)).fetchone() is not None


class BridgeInputUnavailable(RuntimeError):
    """A required bridge input (weights, S&P path, a component series) is absent."""


class WeightsUnavailable(BridgeInputUnavailable):
    """PCE weights are unavailable (bea_pce_detail not built) and approximation not allowed."""


@dataclass
class ComponentValue:
    component: str
    source_type: str
    relative: float | None            # 1 + first-release SA MoM, or None if unavailable
    in_core: bool
    vintage: str                      # first_release | latest_vintage | imputed | absent
    method: str                       # how the relative was produced
    note: str = ""


@dataclass
class BridgeResult:
    ref_month: str
    forecast_time: str
    core_pce_mom: float | None
    weights_basis: str
    components: list[ComponentValue] = field(default_factory=list)
    covered_weight: float = 0.0       # share of core PCE weight actually priced this month
    latest_vintage_weight: float = 0.0  # share read latest-vintage (leakage-exposed)


def _components(mapping_path=MAPPING) -> list[dict]:
    return yaml.safe_load(open(mapping_path))["pce_bridge"]["components"]


def _add_months(month: str, k: int) -> str:
    d = dt.date.fromisoformat(month if len(month) == 10 else month + "-01")
    mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def _official_sa_mom(conn, sid: str, ref: str) -> float | None:
    """Latest-vintage SA MoM from official_current (leakage-exposed for pre-current months —
    caller flags it). SA components are revised only at the annual February seasonal update."""
    lvl = {p: v for p, v in conn.execute(
        "SELECT period, value FROM official_current WHERE series_id=? AND _superseded_by_run_id IS NULL",
        (sid,))}
    pm = _add_months(ref, -1)
    if ref in lvl and pm in lvl and lvl[pm]:
        return lvl[ref] / lvl[pm] - 1.0
    return None


def _cpi_code_mom(tb, conn, vint: set[str], code: str, ref: str, ft) -> tuple[float | None, str]:
    """First-release SA MoM for one CPI item code. Resolve SA (CUSR) if BLS publishes it:
    vintage-correct via timebase where ALFRED-archived, else latest-vintage official_current
    (flagged). If BLS publishes no SA (NSA-only strata), use NSA (CUUR) — which IS first
    release because the NSA index is never revised (3A). Returns (mom, vintage_flag)."""
    sa, nsa = f"CUSR0000{code}", f"CUUR0000{code}"
    if _has_series(conn, sa):
        if sa in vint:
            try:
                return tb.asof_mom_for_ref(sa, ref, ft), "first_release"
            except (NoMomExists, NotYetReleased, PreVintageFloor, UnknownSeries):
                return None, "first_release"
        return _official_sa_mom(conn, sa, ref), "latest_vintage"
    if _has_series(conn, nsa):
        return _official_sa_mom(conn, nsa, ref), "first_release"  # NSA unrevised = first release
    return None, "absent"


def _cpi_relative(tb, conn, vint, codes: list[str], ref: str, ft, ri: dict) -> tuple[float | None, str]:
    """Combine several CPI item strata into one component relative, weighting the sub-strata by
    their CPI relative importances (documented approx — PCE sub-weights need bea_pce_detail).
    Vintage flag is the worst case across sub-strata."""
    num = den = 0.0
    flags = set()
    for code in codes:
        mom, flag = _cpi_code_mom(tb, conn, vint, code, ref, ft)
        if mom is None:
            continue
        w = ri.get(code, 0.0) or 1e-9   # fall back to equal weight if the sub-stratum has no RI
        num += w * (1.0 + mom)
        den += w
        flags.add(flag)
    if den == 0:
        return None, "absent"
    flag = "latest_vintage" if "latest_vintage" in flags else "first_release"
    return num / den, flag


_SP500_CACHE: dict | None = None


def _sp500_mom(conn, ref: str, db_path=DEFAULT_DB) -> float | None:
    """Monthly S&P-500 (equity path) MoM from proxy_observations (source=sp500), monthly
    average vs prior month. The AUM path for portfolio-management fees. Cached per process."""
    global _SP500_CACHE
    if _SP500_CACHE is None:
        from nowcast import alignment
        _SP500_CACHE = alignment.monthly_mom(str(db_path), "sp500", "US")
    return _SP500_CACHE.get(ref)


def _ppi_relative(tb, conn, sid: str, ref: str, ft) -> tuple[float | None, str, str]:
    """(relative, vintage_flag, method). Portfolio-management PPI is discontinued 2022-12 ->
    post-boundary uses the S&P-500 equity path (AUM-based fees). PPI feeders have no ALFRED
    vintages -> latest-vintage, flagged."""
    if sid == "PCU523920523920" and ref > PORTFOLIO_PPI_DISCONTINUED:
        # PPI portfolio-mgmt discontinued 2022-12. The S&P monthly change is a POOR proxy for
        # BEA's asset-based portfolio-mgmt price (DPMIRG) — poorly correlated, sometimes opposite
        # sign (verified against 2.4.4U). No forecastable price signal at forecast time -> frozen.
        return 1.0, "imputed", "frozen(portfolio_no_forecastable_price)"
    mom, flag = (None, "latest_vintage")
    if _has_series(conn, sid):
        mom = _official_sa_mom(conn, sid, ref)
    return (None, "absent", "series_absent") if mom is None else (1.0 + mom, flag, "ppi_relative")


# --- bea_imputed components: documented approximations, frozen (no post-2023 fitting) -------
# Each returns a monthly price relative. Frozen terms are the pre-2023 (<= 2022-12) mean of a
# defensible official proxy, computed once and hard-frozen; rationale in the docstring.

def _imputed_relative(name: str, ref: str, tb, conn, vint: set[str], ft, ri: dict) -> tuple[float | None, str, str]:
    if name == "group_housing":
        # Dormitories/group homes: BEA input-cost imputation tracks shelter. Proxy = tenant
        # rent (SEHA) relative — the same rent process, vintaged (first-release via timebase).
        r, flag = _cpi_code_mom(tb, conn, vint, "SEHA", ref, ft)
        return (None, "absent", "rent_proxy") if r is None else (1.0 + r, flag, "rent_proxy(SEHA)")
    if name == "health_insurance_margin":
        # BEA prices health insurance as a MARGIN (premiums less benefits) — no CPI analogue and
        # highly volatile; without bea_pce_detail it cannot be reconstructed. Frozen carry = 0
        # bp MoM (documented placeholder; a KNOWN unattributable gap, flagged low-confidence).
        return 1.0, "imputed", "frozen_zero(no_analogue)"
    if name == "financial_services_without_payment":
        # H9c FALSIFIED OOS (drift +1.85bp over-corrected 2023+; regime shift as rates rose) ->
        # null restored: freeze-at-zero carry. Residue (Instrument A only). Standing rule: the
        # carry spec is re-selected each January on data through prior year-end (see mapping note).
        return 1.0 + _drift(name), "imputed", "freeze_zero(H9c_falsified)"
    if name == "life_insurance":
        return 1.0, "imputed", "frozen_zero(expected_benefit_margin)"
    if name == "npish_final_consumption":
        # H9c FALSIFIED OOS (drift +0.98bp over-corrected 2023+) -> null restored: freeze-at-zero.
        # Residue (Instrument A only). Standing rule: carry spec re-selected each January (mapping).
        return 1.0 + _drift(name), "imputed", "freeze_zero(H9c_falsified)"
    return None, "absent", "unknown_imputed"


def _drift(name: str) -> float:
    for c in _components():
        if c["component"] == name and c.get("frozen_drift_bp") is not None:
            return c["frozen_drift_bp"] / 10000.0
    return 0.0


def is_residue(name: str) -> bool:
    """A residue component (Instrument A only): no adequate CPI/PPI proxy after the H9 audit
    (corr vs BEA 2.4.4U < 0.5 or carry-only). Excluded from Instrument B (trackable core)."""
    return any(c["component"] == name and c.get("residue") for c in _components())


def _has_bea(conn) -> bool:
    return conn.execute("SELECT 1 FROM official_current WHERE source='bea_pce_detail' LIMIT 1").fetchone() is not None


def bea_weights(ref_year: int, db_path=DEFAULT_DB) -> dict[str, float]:
    """True PCE weights = BEA 2.4.5U nominal shares (bea_weight_code, RC) for the in-core
    components. VINTAGE-APPROPRIATE: the PRIOR calendar year's annual mean nominal — a
    structural annual input, knowable well before any month of ref_year (the user's frequency-
    roles clarification), so it introduces no forecast look-ahead. REVISION HANDLING: annual
    expenditure shares barely move under BEA's monthly/annual/comprehensive revisions, so we
    take the latest-vintage prior-year annual level; bias direction is negligible and, being a
    slow structural share (not a monthly print), does not leak the target. Missing prior-year
    (< 2010) falls back to the earliest available year."""
    py = ref_year - 1
    out: dict[str, float] = {}
    with db.connect(db_path) as conn:
        for c in _components():
            if not c.get("in_core"):
                continue
            code = c.get("bea_weight_code")
            if not code:
                continue
            rows = conn.execute(
                "SELECT value FROM official_current WHERE series_id=? AND period LIKE ? "
                "AND _superseded_by_run_id IS NULL", (code, f"{py}-%")).fetchall()
            if not rows:  # prior year out of range -> earliest available
                rows = conn.execute(
                    "SELECT value FROM official_current WHERE series_id=? AND period LIKE '2010-%' "
                    "AND _superseded_by_run_id IS NULL", (code,)).fetchall()
            out[c["component"]] = sum(float(v) for (v,) in rows) / len(rows) if rows else 0.0
    return out


def pce_weights(ref_month: str | None = None, allow_approximate: bool = False,
                db_path=DEFAULT_DB) -> tuple[dict[str, float], str]:
    """(weights_by_component, basis). Real path: BEA 2.4.5U prior-year annual nominal shares
    (needs ref_month for the vintage year). Fallback (allow_approximate): CPI-relative-
    importance PROXY weights, loudly flagged (the degraded-gate weights — CPI and PCE diverge
    most where the bridge is hardest: healthcare, financial, NPISH). Raises otherwise."""
    with db.connect(db_path) as conn:
        has_bea = _has_bea(conn)
    if has_bea and ref_month is not None:
        yr = int(ref_month[:4])
        return bea_weights(yr, db_path), f"bea_2.4.5U_annual_prioryear({yr - 1})"
    if not allow_approximate:
        raise WeightsUnavailable(
            "PCE weights require bea_pce_detail (Table 2.4.5U) and a ref_month for the vintage "
            "year. Pass allow_approximate=True for CPI-RI proxy weights (flagged, gate-degrading).")
    ri = weights.weights_as_of("2022-06-01", db_path=db_path)  # frozen pre-2023 vintage
    out: dict[str, float] = {}
    for c in _components():
        if not c.get("in_core"):
            continue
        ss = c.get("source_series") or []
        out[c["component"]] = sum(ri.get(s, 0.0) for s in ss) if ss else 0.0
    return out, "cpi_ri_proxy_2022(APPROXIMATE)"


def assemble_core_pce_mom(ref_month: str, forecast_time, allow_approximate_weights: bool = False,
                          exclude_residue: bool = False, db_path=DEFAULT_DB) -> BridgeResult:
    """Assemble unrounded core PCE MoM for ref_month as known at forecast_time (post CPI+PPI
    release). Laspeyres-weighted mean of core component relatives (Fisher approximation).
    `exclude_residue=True` gives Instrument B (trackable core = core ex the 3 H9-residue
    components, renormalized). Every component records its vintage flag and method."""
    from nowcast.timebase import open_timebase

    ft = forecast_time
    wts, basis = pce_weights(ref_month=ref_month, allow_approximate=allow_approximate_weights, db_path=db_path)
    res = BridgeResult(ref_month=ref_month, forecast_time=str(ft), core_pce_mom=None, weights_basis=basis)
    ri = weights.weights_as_of(f"{int(ref_month[:4])}-06-01", db_path=db_path) if _year_covered(ref_month, db_path) \
        else weights.weights_as_of("2022-06-01", db_path=db_path)

    num = den = 0.0
    latest_w = 0.0
    with db.connect(db_path) as conn, open_timebase(db_path) as tb:
        vint = _vintaged_series(conn)
        for c in _components():
            if not c.get("in_core"):
                continue
            if exclude_residue and c.get("residue"):
                continue
            name, st = c["component"], c["source_type"]
            w = wts.get(name, 0.0)
            if st == "cpi_relative":
                rel, flag = _cpi_relative(tb, conn, vint, c["source_series"], ref_month, ft, ri)
                method = "cpi_relative"
            elif st == "ppi_relative":
                rel, flag, method = _ppi_relative(tb, conn, c["source_series"][0], ref_month, ft)
            else:
                rel, flag, method = _imputed_relative(name, ref_month, tb, conn, vint, ft, ri)
            res.components.append(ComponentValue(name, st, rel, True, flag, method, c.get("confidence", "")))
            if rel is not None and w > 0:
                num += w * rel
                den += w
                if flag == "latest_vintage":
                    latest_w += w
    if den > 0:
        res.core_pce_mom = num / den - 1.0
        total_w = sum(wts.get(c["component"], 0.0) for c in _components()
                      if c.get("in_core") and not (exclude_residue and c.get("residue")))
        res.covered_weight = den / total_w if total_w else 0.0
        res.latest_vintage_weight = latest_w / total_w if total_w else 0.0
    return res


def _year_covered(ref_month: str, db_path) -> bool:
    return int(ref_month[:4]) in weights.coverage_years(db_path)


def component_inventory(db_path=DEFAULT_DB) -> list[dict]:
    """Every PCE component classified: implemented | approximated | absent, with the reason
    (vintage status, weight source, S&P/BEA dependency). The CHECKPOINT-1 deliverable."""
    rows = []
    with db.connect(db_path) as conn:
        vintaged = _vintaged_series(conn)
        sp500_ok = _has_proxy(conn, "sp500")
        for c in _components():
            name, st = c["component"], c["source_type"]
            ss = c.get("source_series") or []
            if st == "cpi_relative":
                have = sum(1 for x in ss if _has_series(conn, f"CUSR0000{x}") or _has_series(conn, f"CUUR0000{x}"))
                nvint = sum(1 for x in ss if f"CUSR0000{x}" in vintaged)
                status = "implemented" if have == len(ss) else ("approximated" if have else "absent")
                reason = f"{nvint}/{len(ss)} first-release-vintaged; rest latest-vintage or NSA-first-release"
            elif st == "ppi_relative":
                sid = ss[0]
                if sid == "PCU523920523920":
                    status = "implemented" if sp500_ok else "approximated"
                    reason = "PPI discontinued 2022-12; post-2022 via S&P equity path" + ("" if sp500_ok else " (S&P absent)")
                else:
                    status = "implemented" if _has_series(conn, sid) else "absent"
                    reason = "PPI present, latest-vintage (no ALFRED vintage)" if _has_series(conn, sid) else "PPI series absent"
            else:
                impl = {"group_housing": ("implemented", "rent (SEHA) first-release proxy"),
                        "health_insurance_margin": ("approximated", "frozen zero — no CPI analogue, needs BEA"),
                        "financial_services_without_payment": ("implemented" if sp500_ok else "absent",
                                                               "S&P equity path" if sp500_ok else "needs S&P path"),
                        "life_insurance": ("approximated", "frozen zero — expected-benefit margin"),
                        "npish_final_consumption": ("approximated", "frozen zero — input-cost trend")}
                status, reason = impl.get(name, ("absent", "unknown"))
            rows.append({"component": name, "source_type": st, "in_core": bool(c.get("in_core")),
                         "confidence": c.get("confidence", ""), "status": status, "reason": reason})
    return rows
