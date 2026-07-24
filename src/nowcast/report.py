"""Pre-print one-pager generator + post-print loop (Session 6, Tasks 2/4). Deterministic, offline.

`generate(instrument, ref_month, as_of)` writes docs/prints/{YYYY-MM}_{print}.md: the call with
its band, COIN-FLIP flag, the component attribution table as the centrepiece, a regime line, the
running pristine scorecard, and — so a page is auditable after the fact — the freeze timestamp
and an **information-set hash** (a fingerprint of exactly the observable inputs the call was made
from). `postmortem(...)` populates the realized print, computes the deviation, attributes it
against published components, appends a postmortem section, and updates the ledger row.

Nothing here alters frozen configs or regenerates a past call with today's information: a call is
always built from `as_of`-gated reads, and postmortem only *appends*.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

from nowcast import component_models as CM
from nowcast import db, intramonth, ledger
from nowcast import pce_acceptance as PA
from nowcast import pce_bridge as PB

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "db" / "nowcast.sqlite"
PRINTS = REPO / "docs" / "prints"
TARIFF_REGIME_START = "2025-02-01"

# Band sources (OOS, from evaluation_1.md / the intramonth curve) — stated, never invented.
CPI_TMINUS_BAND = {30: 10.3, 24: 8.8, 18: 8.9, 12: 8.1, 8: 7.5, 5: 7.5, 3: 7.5}
PCE_BAND_BP, PCE_P10, PCE_P90 = 7.97, -11.9, 12.7


def _band_for_days(days: int | None) -> float:
    if days is None:
        return 11.6
    k = min(CPI_TMINUS_BAND, key=lambda d: abs(d - days))
    return CPI_TMINUS_BAND[k]


def _boundary_dist_bp(bp: float) -> float:
    nearest = round((bp - 5) / 10.0) * 10 + 5
    return abs(bp - nearest)


def _regime_line(ref_month: str) -> str:
    era = "post-2023 annual-weight regime" if ref_month >= "2023-01-01" else "pre-2023 biennial-weight era"
    tariff = "; **tariff regime** (post-2025-02 announcements)" if ref_month >= TARIFF_REGIME_START else ""
    return f"{era}{tariff}"


def info_set_hash(instrument: str, ref_month: str, as_of: dt.date, db_path=DEFAULT_DB) -> str:
    """Fingerprint of exactly the observable inputs at as_of — makes a page auditable: re-running
    the same as_of on the same data must reproduce this hash."""
    from nowcast import proxy_timebase as PT
    from nowcast import windows
    parts = [instrument, ref_month, as_of.isoformat()]
    with db.connect(db_path) as conn:
        for src, key in (("eia_gasoline", "US"), ("manheim", "US_full_month")):
            obs = windows._daily_obs(conn, src, key)
            vis = sorted((d, v) for d, v in obs.items() if PT.observed_asof(src, d) <= as_of)
            parts.append(f"{src}:{len(vis)}:{vis[-1] if vis else None}")
        last = conn.execute(
            "SELECT MAX(period) FROM official_current WHERE series_id='CUUR0000SA0' "
            "AND _superseded_by_run_id IS NULL").fetchone()[0]
        parts.append(f"cpi_last_printed:{last}")
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]


def build_call(instrument: str, ref_month: str, as_of: dt.date, db_path=DEFAULT_DB) -> dict:
    """The call record for one print at one as-of. instrument: 'cpi' | 'pce'."""
    with db.connect(db_path) as conn:
        rel = conn.execute(
            "SELECT release_date FROM release_calendar WHERE print=? AND reference_period=? "
            "AND _superseded_by_run_id IS NULL", ("CPI" if instrument == "cpi" else "PCE", ref_month)).fetchone()
    release = dt.date.fromisoformat(rel[0]) if rel else None
    rec = {"instrument": instrument, "ref_month": ref_month, "as_of": as_of.isoformat(),
           "release_date": release.isoformat() if release else None,
           "regime": _regime_line(ref_month), "info_hash": info_set_hash(instrument, ref_month, as_of, db_path)}
    if instrument == "cpi":
        calls, attrib = {}, {}
        for agg in ("headline", "core"):
            r = intramonth.nowcast_as_of(ref_month, as_of, agg, db_path=db_path)
            calls[agg] = round(r["forecast_mom"] * 10000, 1) if r["forecast_mom"] is not None else None
            rec["frozen"] = r["frozen"]; rec["days_to_release"] = r["days_to_release"]
            rec["effective_asof"] = r["effective_asof"]
        cfg = CM._cfg()
        eff = dt.date.fromisoformat(rec["effective_asof"])
        for code in cfg["components"]:
            f = CM.forecast_component(code, ref_month, eff, cfg, db_path)
            if f is not None:
                attrib[code] = round(f * 10000, 1)
        rec.update({"call_bp": calls["headline"], "call_core_bp": calls["core"],
                    "band_bp": _band_for_days(rec["days_to_release"]), "attribution": attrib})
    else:
        from zoneinfo import ZoneInfo
        ft = dt.datetime.combine(as_of, dt.time(12, 0), tzinfo=ZoneInfo("America/New_York"))
        res = PB.assemble_core_pce_mom(ref_month, ft, db_path=db_path)
        rec.update({"call_bp": round(res.core_pce_mom * 10000, 1) if res.core_pce_mom is not None else None,
                    "call_core_bp": None, "band_bp": PCE_BAND_BP, "frozen": True,
                    "days_to_release": (release - as_of).days if release else None,
                    "effective_asof": as_of.isoformat(),
                    "attribution": {c.component: round((c.relative - 1) * 10000, 1)
                                    for c in res.components if c.relative is not None}})
    if rec.get("call_bp") is not None:
        d = _boundary_dist_bp(rec["call_bp"])
        rec["coin_flip"] = d < 1.5
        rec["boundary_dist_bp"] = round(d, 2)
    return rec


def _scorecard() -> str:
    rows = ledger.read_rows()
    done = [r for r in rows if r.get("realized_bp") not in (None, "", "—")]
    if not done:
        return ("_No pristine call has been graded yet — this ledger starts today. Entries populate "
                "at each print; misses will appear here as prominently as hits._")
    hits = [r for r in done if abs(float(r["deviation_bp"])) <= float(r["band_bp"])]
    lines = ["| ref | instrument | call | realized | deviation | within band |", "|---|---|--:|--:|--:|:--:|"]
    for r in done:
        ok = abs(float(r["deviation_bp"])) <= float(r["band_bp"])
        lines.append(f"| {r['ref_month'][:7]} | {r['instrument']} | {r['call_bp']} | {r['realized_bp']} | "
                     f"{r['deviation_bp']} | {'yes' if ok else '**NO**'} |")
    lines.append("")
    lines.append(f"**{len(hits)}/{len(done)} within band.** Misses are listed above, not summarised away.")
    return "\n".join(lines)


def render_page(rec: dict) -> str:
    inst = "CPI" if rec["instrument"] == "cpi" else "core PCE"
    frozen = "**FROZEN**" if rec.get("frozen") else "**NOT FROZEN** (pre-freeze; will move)"
    cf = ""
    if rec.get("coin_flip"):
        cf = (f"\n> **COIN-FLIP** — the call sits {rec['boundary_dist_bp']} bp from a 0.1% rounding "
              f"boundary. Which way it rounds is a toss-up; treat the rounded print as unresolved.\n")
    att = "\n".join(f"| {k} | {v:+.1f} |" for k, v in sorted(rec["attribution"].items(), key=lambda kv: -abs(kv[1]))[:12])
    core = f"\n- **Core:** {rec['call_core_bp']:+.1f} bp" if rec.get("call_core_bp") is not None else ""
    return f"""# {rec['ref_month'][:7]} {inst} — pre-print call

**Call: {rec['call_bp']:+.1f} bp** MoM, band **±{rec['band_bp']:.1f} bp**.{core}

*Every number below states what it is measured against.*

| field | value | reference |
|---|---|---|
| call | {rec['call_bp']:+.1f} bp | predicted **first-release** MoM (NSA for CPI; core PCE for PCE) |
| band | ±{rec['band_bp']:.1f} bp | OOS MAE at this lead ({'intramonth T-minus curve' if rec['instrument']=='cpi' else 'evaluation_1.md, 10–90 [' + str(PCE_P10) + ', ' + str(PCE_P90) + ']'}) |
| as-of | {rec['as_of']} | information cutoff; effective {rec['effective_asof']} |
| status | {frozen} | freeze at T-4 (availability_calendar) |
| release | {rec['release_date']} | T-{rec['days_to_release']} from as-of |
| regime | {rec['regime']} | reporting label only |
| info-set hash | `{rec['info_hash']}` | re-running this as-of on the same data must reproduce it |
{cf}
## Component attribution (centrepiece)

Each component's own predicted MoM contribution at this as-of:

| component | predicted MoM (bp) |
|---|--:|
{att}

## Running pristine scorecard

{_scorecard()}

---
*Generated by `src/nowcast/report.py` from frozen admitted configs. Not desk-distributed
automatically; no number here is a consensus comparison (no licensed consensus feed).*
"""


def generate(instrument: str, ref_month: str, as_of: dt.date, db_path=DEFAULT_DB, append_ledger=True) -> Path:
    PRINTS.mkdir(parents=True, exist_ok=True)
    rec = build_call(instrument, ref_month, as_of, db_path)
    path = PRINTS / f"{ref_month[:7]}_{instrument}.md"
    path.write_text(render_page(rec))
    if append_ledger:
        ledger.append_call(rec)
    return path


def postmortem(instrument: str, ref_month: str, db_path=DEFAULT_DB, dry_run: bool = False) -> dict:
    """Populate the realized print, compute the deviation, attribute it against published
    components, APPEND a postmortem section to the page and update the ledger row.

    `dry_run=True` exercises the whole path on an ALREADY-COMPLETED print without touching the
    pristine ledger: the call is rebuilt at that print's T-3 freeze (a replay — explicitly NOT a
    pristine forward call) and the output goes to a *_DRYRUN page. This is how the loop is proven
    before a live print needs it, without contaminating the forward record."""
    path = PRINTS / f"{ref_month[:7]}_{instrument}.md"
    if dry_run:
        with db.connect(db_path) as conn:
            rel = conn.execute(
                "SELECT release_date FROM release_calendar WHERE print=? AND reference_period=? "
                "AND _superseded_by_run_id IS NULL",
                ("CPI" if instrument == "cpi" else "PCE", ref_month)).fetchone()
        asof = dt.date.fromisoformat(rel[0]) - dt.timedelta(days=3) if rel else dt.date.today()
        rec = build_call(instrument, ref_month, asof, db_path)
        row = {"call_bp": f"{rec['call_bp']:+.1f}", "band_bp": f"{rec['band_bp']:.1f}"}
        path = PRINTS / f"{ref_month[:7]}_{instrument}_DRYRUN.md"
        path.write_text(render_page(rec) + "\n> **DRY RUN — replay of a completed print. NOT a "
                                           "pristine forward call; not in the ledger.**\n")
    else:
        row = ledger.find_row(instrument, ref_month)
    if row is None:
        return {"error": "no ledger row"}
    with db.connect(db_path) as conn:
        if instrument == "cpi":
            from nowcast import event_study as ES
            realized = ES._nsa_mom(conn, "CUUR0000SA0", ref_month)
        else:
            r = conn.execute("SELECT mom FROM first_release_mom WHERE series_id='PCEPILFE' "
                             "AND reference_period=?", (ref_month,)).fetchone()
            realized = r[0] if r else None
    if realized is None:
        return {"status": "pending", "reason": "print not yet released / first-release unavailable"}
    realized_bp = round(realized * 10000, 1)
    dev = round(float(row["call_bp"]) - realized_bp, 1)
    within = abs(dev) <= float(row["band_bp"])
    # attribution vs published components (PCE waits for BEA 2.4.4U)
    attrib_note, attrib_rows = "", []
    if instrument == "pce":
        rows = PA.attribution_vs_bea(ref_month, db_path=db_path)
        if rows:
            attrib_rows = rows[:8]
        else:
            attrib_note = "BEA 2.4.4U component prices for this month are not published yet — component attribution populates on the next BEA release."
    else:
        attrib_note = "CPI component attribution: see `event_study_results.csv` for the frozen per-component calls; published stratum detail is in `official_current`."
    sec = [f"\n\n---\n\n## Postmortem (appended {dt.date.today().isoformat()})\n",
           f"| field | value |\n|---|--:|",
           f"| realized first-release | {realized_bp:+.1f} bp |",
           f"| call | {row['call_bp']} bp |",
           f"| **deviation** | **{dev:+.1f} bp** |",
           f"| within band (±{row['band_bp']}) | {'yes' if within else '**NO — miss**'} |"]
    if attrib_rows:
        sec += ["\n**Deviation attribution vs published components (bp):**\n",
                "| component | contribution | bridge | actual |", "|---|--:|--:|--:|"]
        sec += [f"| {r['component']} | {r['contrib_bp']:+.2f} | {r['bridge_mom_bp']:+.1f} | {r['bea_actual_bp']:+.1f} |"
                for r in attrib_rows]
    if attrib_note:
        sec.append(f"\n_{attrib_note}_")
    if path.exists():
        path.write_text(path.read_text() + "\n".join(sec) + "\n")
    if not dry_run:
        ledger.populate_realized(instrument, ref_month, realized_bp, dev, "within band" if within else "MISS")
    return {"status": "dry_run" if dry_run else "done", "page": path.name, "call_bp": float(row["call_bp"]),
            "realized_bp": realized_bp, "deviation_bp": dev, "within_band": within,
            "attribution_rows": len(attrib_rows)}
