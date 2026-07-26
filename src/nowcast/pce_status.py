"""PCE standing-call status report — regenerable daily until the print lands.

Generates `docs/pce_status_report.md` for the live PCE ledger row, and maintains an append-only
daily check log (`docs/pce_status_log.csv`). Designed to be run once a day:

    python -c "from nowcast import pce_status; pce_status.update()"

HARD BOUNDARY: this module never adjudicates. It reads the ledger and the DB; if the print has not
been published it records `realized = pending` and says so. It never writes a realized value, never
regenerates the frozen call, and never touches a config. On/after the release date it reports that
the print is due and defers population to `report.postmortem` per the runbook.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

import numpy as np

from nowcast import db, ledger

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "db" / "nowcast.sqlite"
DOC = REPO / "docs" / "pce_status_report.md"
LOG = REPO / "docs" / "pce_status_log.csv"
LOG_COLS = ["check_date", "days_to_print", "realized_status", "call_bp", "ledger_hash", "note"]
INSTRUMENT, REF_MONTH = "pce", "2026-06-01"
PCE_SERIES = "PCEPILFE"
INCREMENT_BP = 10.0          # one published 0.1 pp increment
COIN_FLIP_BP = 1.5


def _release_date(conn, ref_month: str) -> dt.date | None:
    r = conn.execute(
        "SELECT release_date FROM release_calendar WHERE print='PCE' AND reference_period=? "
        "AND _superseded_by_run_id IS NULL", (ref_month,)).fetchone()
    return dt.date.fromisoformat(r[0]) if r else None


def realized_status(ref_month: str = REF_MONTH, db_path=DEFAULT_DB) -> tuple[str, float | None]:
    """('published', mom_bp) once the first release exists; ('pending', None) otherwise.

    The check is data-driven, not date-driven: a print counts as landed only when its first-release
    MoM is actually in the DB.
    """
    with db.connect(db_path) as conn:
        r = conn.execute(
            "SELECT mom FROM first_release_mom WHERE series_id=? AND reference_period=?",
            (PCE_SERIES, ref_month)).fetchone()
    if r and r[0] is not None:
        return "published", float(r[0]) * 1e4
    return "pending", None


def band_from_history(db_path=DEFAULT_DB) -> dict:
    """Empirical error distribution of Instrument A over the standard window (bp)."""
    from nowcast import pce_acceptance as PA
    acc = PA.evaluate("2023-01-01", "2026-05-01", "A", db_path=db_path)
    e = np.array([m.err_bp for m in acc.months])
    ab = np.abs(e)
    return {"n": int(len(e)), "mae": float(ab.mean()), "bias": float(e.mean()),
            "p10": float(np.percentile(e, 10)), "p90": float(np.percentile(e, 90)),
            "within_half": float((ab < INCREMENT_BP / 2).mean()),
            "within_one": float((ab < INCREMENT_BP).mean()),
            "two_plus": float((ab >= 2 * INCREMENT_BP).mean()),
            "coin_flip": int(sum(1 for m in acc.months if m.coin_flip)),
            "correct_side": int(sum(1 for m in acc.months if m.correct_side)),
            "months": int(len(acc.months))}


def implied_yoy(call_bp: float, ref_month: str = REF_MONTH, db_path=DEFAULT_DB) -> dict | None:
    """YoY implied by our single MoM call plus the 11 already-published months.

    IMPORTANT (CLAUDE.md rule 8): YoY is **never a target or an evaluation metric** here — overlapping
    12-month windows make YoY error series autocorrelated, which is exactly the leakage rule 8 forbids.
    This is a *reporting* transform: given published index levels, our one MoM call *determines* the
    YoY figure, so it adds no new claim and its uncertainty is exactly the MoM uncertainty.
    """
    base = _add_months(ref_month, -12)
    prev = _add_months(ref_month, -1)
    with db.connect(db_path) as conn:
        lv = {p: float(v) for p, v in conn.execute(
            "SELECT reference_period, latest_value FROM latest_value WHERE series_id=? "
            "AND reference_period IN (?,?,?)", (PCE_SERIES, base, prev, _add_months(base, -1)))}
    if base not in lv or prev not in lv:
        return None
    idx = lv[prev] * (1 + call_bp / 1e4)
    out = {"base_month": base, "base_level": lv[base], "prev_level": lv[prev],
           "implied_yoy_pct": (idx / lv[base] - 1) * 100}
    pb = _add_months(base, -1)
    if pb in lv:
        out["published_prev_yoy_pct"] = (lv[prev] / lv[pb] - 1) * 100
    return out


def _add_months(m: str, k: int) -> str:
    d = dt.date.fromisoformat(m)
    mo = d.month - 1 + k
    return dt.date(d.year + mo // 12, mo % 12 + 1, 1).isoformat()


def read_log() -> list[dict]:
    if not LOG.exists():
        return []
    with open(LOG) as f:
        return list(csv.DictReader(f))


def append_log(rec: dict) -> bool:
    """Append one daily check. Idempotent per date: re-running the same day does not duplicate."""
    rows = read_log()
    if any(r["check_date"] == rec["check_date"] for r in rows):
        return False
    LOG.parent.mkdir(parents=True, exist_ok=True)
    new = not LOG.exists()
    with open(LOG, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLS)
        if new:
            w.writeheader()
        w.writerow({c: rec.get(c, "") for c in LOG_COLS})
    return True


def update(as_of: dt.date | None = None, db_path=DEFAULT_DB) -> Path:
    """Append today's check and regenerate the report. Safe to run daily."""
    as_of = as_of or dt.date.today()
    row = ledger.find_row(INSTRUMENT, REF_MONTH)
    if row is None:
        raise RuntimeError(f"no ledger row for {INSTRUMENT} {REF_MONTH}")
    with db.connect(db_path) as conn:
        rel = _release_date(conn, REF_MONTH)
    status, realized = realized_status(REF_MONTH, db_path)
    dtp = (rel - as_of).days if rel else None
    note = ("print not yet published; call stands frozen" if status == "pending"
            else "print published — run report.postmortem to adjudicate (this module never populates)")
    append_log({"check_date": as_of.isoformat(), "days_to_print": dtp, "realized_status": status,
                "call_bp": row["call_bp"], "ledger_hash": row["row_hash"], "note": note})
    DOC.write_text(render(as_of=as_of, db_path=db_path))
    return DOC


def render(as_of: dt.date | None = None, db_path=DEFAULT_DB) -> str:
    as_of = as_of or dt.date.today()
    row = ledger.find_row(INSTRUMENT, REF_MONTH)
    with db.connect(db_path) as conn:
        rel = _release_date(conn, REF_MONTH)
    status, realized = realized_status(REF_MONTH, db_path)
    h = band_from_history(db_path)
    call, band = float(row["call_bp"]), float(row["band_bp"])
    lo, hi = call - h["p90"], call - h["p10"]
    dtp = (rel - as_of).days if rel else None
    dist = min(abs(call - 5.0), abs(call - 15.0))
    groups = _group_table()
    log = read_log()
    logrows = "\n".join(
        f"| {r['check_date']} | {r['days_to_print']} | {r['realized_status']} | {r['call_bp']} | {r['note']} |"
        for r in log) or "| — | — | — | — | (no checks logged yet) |"

    yoy = implied_yoy(call, REF_MONTH, db_path)
    y_lo = implied_yoy(lo, REF_MONTH, db_path)
    y_hi = implied_yoy(hi, REF_MONTH, db_path)

    if status == "published":
        head = (f"**PRINT PUBLISHED.** First-release core PCE MoM = **{realized / 100:+.3f} pp** "
                f"({realized:+.1f} bp). This report does NOT adjudicate — run "
                f"`report.postmortem('pce','{REF_MONTH}')` per the runbook to populate the ledger.")
    else:
        tminus = f"T−{dtp}" if dtp is not None and dtp > 0 else f"T+{abs(dtp)}" if dtp else "T+0"
        head = (f"**STANDING PREDICTION — NOT GRADED.** The print is due **{rel}** — "
                f"**{tminus}** as of {as_of}. The first-release value is not in the DB, so "
                f"`realized` is **pending**; no value is imputed.")

    yoy_block = "_index levels unavailable — YoY not computed_"
    if yoy:
        prev_y = (f"{yoy['published_prev_yoy_pct']:+.2f}%" if "published_prev_yoy_pct" in yoy else "n/a")
        rng = (f"[{y_lo['implied_yoy_pct']:+.2f}%, {y_hi['implied_yoy_pct']:+.2f}%]"
               if y_lo and y_hi else "n/a")
        yoy_block = f"""| figure | value | rounds to |
|---|--:|--:|
| last published YoY ({_add_months(REF_MONTH, -1)[:7]}) | {prev_y} | — |
| **implied YoY for {REF_MONTH[:7]}** | **{yoy['implied_yoy_pct']:+.3f}%** | **{round(yoy['implied_yoy_pct'], 1):+.1f}%** |
| implied 80% YoY range | {rng} | — |

Base month {yoy['base_month'][:7]} index = {yoy['base_level']:.3f}; {_add_months(REF_MONTH, -1)[:7]} = {yoy['prev_level']:.3f}.

**Why YoY is reported but never scored.** CLAUDE.md rule 8 bars YoY *targets* — overlapping 12-month
windows autocorrelate the error series and inflate apparent skill. Here YoY is a **deterministic
transform**: eleven of the twelve months are already published, so our single MoM call *determines*
the YoY figure. It therefore adds **no independent claim**, and its uncertainty is exactly the MoM
uncertainty — which is why the YoY range above is simply the MoM range re-expressed. The **MoM figure
is the scored quantity**; YoY is release context only. (Caveat: BEA revises the index, so the base
month can shift slightly and move YoY without our call changing.)"""

    return f"""# PCE status report — ledger entry #{row['n']}, core PCE {REF_MONTH[:7]}

**Report date: {as_of}** · regenerate daily with
`python -c "from nowcast import pce_status; pce_status.update()"` · generated by
`src/nowcast/pce_status.py`

{head}

**Units: all figures in percentage points (pp), the release convention.** BEA publishes core PCE to
one decimal place, so **one published increment = 0.1 pp**. Basis points are given in parentheses
where a decomposition needs the finer grain (1 pp = 100 bp).

## The call (frozen — immutable)

### MoM — the scored quantity

| field | value |
|---|---|
| instrument | core PCE **MoM**, first release |
| reference month | **{REF_MONTH[:7]}** |
| **call** | **{call / 100:+.3f} pp** ({call:+.1f} bp) → prints as **{round(call / INCREMENT_BP) / 10:+.1f}%** |
| band (at that lead) | ±{band / 100:.3f} pp (±{band:.1f} bp) |
| frozen as-of | **{row['as_of']}** (CPI-day call; ~16 days before the PCE print) |
| release date | **{rel}** |
| realized | **{row['realized_bp']}** |
| verdict | **{row['verdict']}** |
| row hash | `{row['row_hash']}` |

Distance to the nearest 0.1 pp rounding boundary: **{dist / 100:.3f} pp** ({dist:.1f} bp)
({'COIN-FLIP — the rounding is a toss-up, reported not scored' if dist < COIN_FLIP_BP else f'not a coin-flip (threshold {COIN_FLIP_BP / 100:.3f} pp)'}).

### YoY — release context, **not** a scored target

{yoy_block}

## Confidence range (empirical, n={h['n']})

Built from Instrument A's own historical error distribution over 2023-01 → 2026-05 — **not** a fitted
predictive distribution.

| statistic | pp | bp | vs one 0.1 pp increment |
|---|--:|--:|--:|
| MAE | **{h['mae'] / 100:.3f}** | {h['mae']:.2f} | **{h['mae'] / INCREMENT_BP:.2f}×** |
| mean signed bias | {h['bias'] / 100:+.3f} | {h['bias']:+.2f} | essentially unbiased |
| 80% error range | [{h['p10'] / 100:+.3f}, {h['p90'] / 100:+.3f}] | [{h['p10']:+.1f}, {h['p90']:+.1f}] | — |
| **implied 80% range, MoM print** | **[{lo / 100:+.3f}, {hi / 100:+.3f}]** | [{lo:+.1f}, {hi:+.1f}] | — |

### The metric that drives the headline reaction

The market reacts to the **published tenth**, so the decision-relevant score is whether our call lands
in the same 0.1 pp bucket as the actual — not unrounded MAE.

| | value |
|---|--:|
| **same-tenth hit rate (Instrument A, 2023+)** | **38%** (15/40) |
| within half an increment (±0.05 pp) | {h['within_half']:.0%} |
| within one increment (±0.1 pp) | {h['within_one']:.0%} |
| two or more increments off | {h['two_plus']:.0%} |
| COIN-FLIP months (rounding a toss-up by construction) | {h['coin_flip']}/{h['months']} |

**Why the hit rate is only ~38%:** landing in the right tenth generally needs **|error| < 0.05 pp**,
and our MAE is **{h['mae'] / 100:.3f} pp** — about **{h['mae'] / 5.0:.1f}×** that threshold. The
objective is accuracy-bound, not rule-bound; see `docs/rounded_objective.md` for the sensitivity
analysis and for consensus's own hit rate on the same months (78% on PCE — the market's number is
better at this, while our edge stays speed + attribution).

## Where the error comes from, by PCE group

Gross = mean |weighted component error| vs BEA 2.4.4U actuals; signed shows offsetting. At group level
the numbers are small in pp, so bp is shown alongside. Full method and the per-component league table:
`docs/pce_wedge_decomposition.md`.

| PCE group | gross pp | gross bp | signed bp | components |
|---|--:|--:|--:|--:|
{groups}
| **residue lines** *(separate, never blended)* | **0.081** | **8.11** | −3.72 | 3 |

**The floor is a cancellation equilibrium.** Gross component error ≈ **0.318 pp/month** (31.8 bp) nets
down to a **{h['mae'] / 100:.3f} pp** ({h['mae']:.1f} bp) miss — a **4.0×** offset ratio. Accuracy comes
from errors cancelling, not from components tracking well; a month where they align is materially worse
(worst observed 0.245 pp). Mapping explains **82.2%** of monthly error variance; weight vintage only
**0.2%** (H16 null).

## Daily check log (append-only)

| date | T-minus | realized | call | note |
|---|--:|---|--:|---|
{logrows}

---
*Nothing here adjudicates, refits, or alters the frozen call. Adjudication happens on the release
date via `report.postmortem`, per `docs/runbook.md`.*
"""



def _group_table() -> str:
    """PCE-group roll-up of the wedge league table (grouping static; values from H17).

    Shown in pp (release convention) with bp alongside, because group-level magnitudes are small
    in pp. Signed column exposes the offsetting that makes the net error ~4x smaller than gross.
    """
    rows = [("durable goods", 5.26, +0.44, 5), ("transportation svcs", 5.16, +0.27, 3),
            ("health care", 3.67, -0.91, 6), ("financial & insurance", 2.94, -0.39, 2),
            ("other services", 2.37, +0.13, 4), ("nondurable goods", 1.98, +0.25, 5),
            ("recreation svcs", 1.27, +0.03, 1), ("food svcs & accommodation", 1.21, +0.02, 1),
            ("housing & utilities", 0.24, +0.02, 4)]
    return "\n".join(f"| {n} | {g / 100:.3f} | {g:.2f} | {s:+.2f} | {c} |" for n, g, s, c in rows)
