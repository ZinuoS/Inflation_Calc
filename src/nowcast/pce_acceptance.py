"""PCE-bridge acceptance evaluation (Session 3B, Task 2). Deterministic, offline (rule 4).

For each PCE reference month: run the bridge at forecast_time = the CPI release date for that
month (post CPI+PPI), compare the unrounded core-PCE-MoM call to the FIRST-RELEASE PCEPILFE
MoM (via timebase, never latest-vintage). Two tiers:
  TIER 1 — MAE <= 2.0 bp (stretch 1.5 ex-COVID).
  TIER 2 — >= 85% correct side of the 0.x5 (0.1%) rounding boundary among months where the
           call sits >= 1.5 bp from the boundary; inside-band months flagged COIN-FLIP.
Shutdown / not-yet-released months are skipped and counted (never imputed). Per-era (pre/post
2023 biennial->annual weight break) annotation; February months flagged (factor seam).

The bridge has NO fitted parameters (frozen 2022 CPI-RI proxy weights; imputed terms frozen at
documented values) so there is no estimation-window to leak; any future calibration term must
be estimated on <=2022 data and frozen (enforced by keeping this module fit-free)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from nowcast import db, pce_bridge
from nowcast.timebase import ET, NoMomExists, NotYetReleased, UnknownSeries, open_timebase

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"
COVID_MONTHS = {f"2020-{m:02d}-01" for m in range(3, 9)} | {"2021-03-01", "2021-04-01"}


@dataclass
class MonthEval:
    ref_month: str
    bridge_bp: float
    actual_bp: float
    err_bp: float
    era: str
    is_february: bool
    covered_weight: float
    latest_vintage_weight: float
    boundary_dist_bp: float       # bridge call's distance to nearest 0.1% rounding boundary
    correct_side: bool            # bridge and actual round to the same 0.1%
    coin_flip: bool               # bridge call within 1.5 bp of a boundary


@dataclass
class Acceptance:
    months: list[MonthEval] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    weights_basis: str = ""


def _cpi_release_ft(conn, ref_month: str) -> dt.datetime | None:
    r = conn.execute(
        "SELECT release_date FROM release_calendar WHERE print='CPI' AND reference_period=? "
        "AND _superseded_by_run_id IS NULL", (ref_month,)).fetchone()
    if not r:
        return None
    return dt.datetime.fromisoformat(r[0] + "T12:00:00").replace(tzinfo=ET)


def _reported_tenths(bp: float) -> int:
    """Core PCE MoM as the press reports it: rounded to 0.1% (nearest 10 bp)."""
    return round(bp / 10.0)


def _boundary_dist(bp: float) -> float:
    """Distance in bp to the nearest 0.x5 rounding boundary (5, 15, 25, ... bp)."""
    nearest = round((bp - 5) / 10.0) * 10 + 5
    return abs(bp - nearest)


def evaluate(start: str, end: str, db_path=DEFAULT_DB) -> Acceptance:
    out = Acceptance()
    months = _month_range(start, end)
    with db.connect(db_path) as conn, open_timebase(db_path) as tb:
        for m in months:
            ft = _cpi_release_ft(conn, m)
            if ft is None:
                out.skipped.append((m, "no CPI release date")); continue
            # First-release PCEPILFE MoM: the canonical within-vintage first release (the value
            # BEA first printed) = the first_release_mom view, which is the asof_mom_for_ref
            # value evaluated at PCE's own release time. Using the view avoids the PCE
            # release-calendar reference_period convention offset (data-month vs release-month).
            row = conn.execute(
                "SELECT mom FROM first_release_mom WHERE series_id='PCEPILFE' AND reference_period=?", (m,)).fetchone()
            if row is None or row[0] is None:
                out.skipped.append((m, "PCE first release unavailable (shutdown/not released)")); continue
            actual = row[0]
            res = pce_bridge.assemble_core_pce_mom(m, ft, allow_approximate_weights=True, db_path=db_path)
            if res.core_pce_mom is None:
                out.skipped.append((m, "bridge produced no estimate")); continue
            out.weights_basis = res.weights_basis
            b_bp, a_bp = res.core_pce_mom * 10000, actual * 10000
            out.months.append(MonthEval(
                ref_month=m, bridge_bp=round(b_bp, 2), actual_bp=round(a_bp, 2),
                err_bp=round(b_bp - a_bp, 2), era="pre_2023" if m < "2023-01-01" else "post_2023",
                is_february=m[5:7] == "02", covered_weight=round(res.covered_weight, 4),
                latest_vintage_weight=round(res.latest_vintage_weight, 4),
                boundary_dist_bp=round(_boundary_dist(b_bp), 2),
                correct_side=_reported_tenths(b_bp) == _reported_tenths(a_bp),
                coin_flip=_boundary_dist(b_bp) < 1.5))
    return out


def _pce_target_ft(conn, ref_month: str) -> dt.datetime:
    """Forecast time for reading the first-release PCE target: the PCE release date for the
    month (a day after), so asof_mom_for_ref returns the first print, not a later revision."""
    r = conn.execute(
        "SELECT release_date FROM release_calendar WHERE print='PCE' AND reference_period=? "
        "AND _superseded_by_run_id IS NULL", (ref_month,)).fetchone()
    if r:
        return dt.datetime.fromisoformat(r[0] + "T23:59:00").replace(tzinfo=ET) + dt.timedelta(days=1)
    # fallback: ~end of month+1 (PCE lands ~4 weeks after the reference month)
    d = dt.date.fromisoformat(ref_month)
    return dt.datetime(d.year + (d.month == 12), (d.month % 12) + 1, 28, tzinfo=ET) + dt.timedelta(days=7)


def _month_range(start: str, end: str) -> list[str]:
    out, d = [], dt.date.fromisoformat(start)
    last = dt.date.fromisoformat(end)
    while d <= last:
        out.append(d.isoformat())
        d = dt.date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
    return out


def summarize(acc: Acceptance, ex_covid: bool = False) -> dict:
    import numpy as np
    ms = [x for x in acc.months if not (ex_covid and x.ref_month in COVID_MONTHS)]
    if not ms:
        return {"n": 0}
    errs = np.array([abs(x.err_bp) for x in ms])
    graded = [x for x in ms if not x.coin_flip]
    correct = [x for x in graded if x.correct_side]
    def mae(xs):
        return round(float(np.mean([abs(x.err_bp) for x in xs])), 2) if xs else None
    return {
        "n": len(ms), "mae_bp": round(float(errs.mean()), 2), "median_bp": round(float(np.median(errs)), 2),
        "max_bp": round(float(errs.max()), 2),
        "tier1_pass": bool(errs.mean() <= 2.0),
        "mae_pre_2023": mae([x for x in ms if x.era == "pre_2023"]),
        "mae_post_2023": mae([x for x in ms if x.era == "post_2023"]),
        "mae_february": mae([x for x in ms if x.is_february]),
        "n_graded": len(graded), "n_coin_flip": len(ms) - len(graded),
        "tier2_correct_side_pct": round(100 * len(correct) / len(graded), 1) if graded else None,
        "tier2_pass": bool(graded and len(correct) / len(graded) >= 0.85),
        "mean_latest_vintage_weight": round(float(np.mean([x.latest_vintage_weight for x in ms])), 3),
    }


def attribution(acc: Acceptance, ref_month: str, db_path=DEFAULT_DB) -> list[dict]:
    """Degraded-mode attribution for a miss: each component's weighted contribution to the
    bridge MoM, ranked by |contribution|. Without BEA per-component actuals we can rank the
    CPI/PPI drivers but cannot verify them; imputed/frozen/equity components are marked
    unattributable."""
    me = next((x for x in acc.months if x.ref_month == ref_month), None)
    if me is None:
        return []
    ft = None
    with db.connect(db_path) as conn:
        ft = _cpi_release_ft(conn, ref_month)
    res = pce_bridge.assemble_core_pce_mom(ref_month, ft, allow_approximate_weights=True, db_path=db_path)
    wts, _ = pce_bridge.pce_weights(allow_approximate=True, db_path=db_path)
    tot = sum(wts.get(c.component, 0.0) for c in res.components if c.relative is not None)
    rows = []
    for cv in res.components:
        if cv.relative is None:
            continue
        w = wts.get(cv.component, 0.0)
        contrib_bp = (w / tot) * (cv.relative - 1.0) * 10000 if tot else 0.0
        rows.append({"component": cv.component, "contrib_bp": round(contrib_bp, 2),
                     "vintage": cv.vintage, "method": cv.method,
                     "attributable": cv.vintage not in ("imputed", "equity_path")})
    rows.sort(key=lambda r: -abs(r["contrib_bp"]))
    return rows
