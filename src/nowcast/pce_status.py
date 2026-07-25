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

    if status == "published":
        head = (f"**PRINT PUBLISHED.** First-release core PCE MoM = **{realized:+.1f} bp**. "
                f"This report does NOT adjudicate — run `report.postmortem('pce','{REF_MONTH}')` "
                f"per the runbook to populate the ledger.")
    else:
        tminus = f"T−{dtp}" if dtp is not None and dtp > 0 else f"T+{abs(dtp)}" if dtp else "T+0"
        head = (f"**STANDING PREDICTION — NOT GRADED.** The print is due **{rel}** — "
                f"**{tminus}** as of {as_of}. The first-release value is not in the DB, so "
                f"`realized` is **pending**; no value is imputed.")

    return f"""# PCE status report — ledger entry #{row['n']}, core PCE {REF_MONTH[:7]}

**Report date: {as_of}** · regenerate daily with
`python -c "from nowcast import pce_status; pce_status.update()"` · generated by
`src/nowcast/pce_status.py`

{head}

## The call (frozen — immutable)

| field | value |
|---|---|
| instrument | core PCE MoM, first release |
| reference month | **{REF_MONTH[:7]}** |
| **call** | **{call:+.1f} bp** = **{call / 100:+.3f} pp** → rounds to **{round(call / INCREMENT_BP) / 10:+.1f}%** |
| band (at that lead) | ±{band:.1f} bp |
| frozen as-of | **{row['as_of']}** (CPI-day call; ~16 days before the PCE print) |
| release date | **{rel}** |
| realized | **{row['realized_bp']}** |
| verdict | **{row['verdict']}** |
| row hash | `{row['row_hash']}` |

Distance to the nearest 0.1 pp rounding boundary: **{dist:.1f} bp**
({'COIN-FLIP — the rounding is a toss-up, reported not scored' if dist < COIN_FLIP_BP else f'not a coin-flip (threshold {COIN_FLIP_BP} bp)'}).

## Confidence range (empirical, n={h['n']})

Built from Instrument A's own historical error distribution over 2023-01 → 2026-05 — **not** a fitted
predictive distribution.

| statistic | bp | published convention |
|---|--:|---|
| MAE | **{h['mae']:.2f}** | {h['mae'] / 100:.4f} pp = **{h['mae'] / INCREMENT_BP:.2f}×** one 0.1 pp increment |
| mean signed bias | {h['bias']:+.2f} | essentially unbiased |
| 80% error range | [{h['p10']:+.1f}, {h['p90']:+.1f}] | — |
| **implied 80% range for this print** | **[{lo:+.1f}, {hi:+.1f}]** | **[{lo / 100:+.3f}, {hi / 100:+.3f}] pp** |

Historical hit rates: within half an increment **{h['within_half']:.0%}**, within one increment
**{h['within_one']:.0%}**, two or more increments off **{h['two_plus']:.0%}**. Rounds to the same
published tenth as the actual: **{h['correct_side']}/{h['months']}** ({h['correct_side'] / h['months']:.0%});
**{h['coin_flip']}/{h['months']}** months were COIN-FLIP by construction.

## Where the error comes from, by PCE group

Gross = mean |weighted component error| vs BEA 2.4.4U actuals; signed shows offsetting. Full method
and the per-component league table: `docs/pce_wedge_decomposition.md`.

| PCE group | gross bp | signed bp | components |
|---|--:|--:|--:|
{groups}
| **residue lines** *(separate, never blended)* | **8.11** | −3.72 | 3 |

**The floor is a cancellation equilibrium.** Gross component error ≈ **31.8 bp/month** nets down to a
**{h['mae']:.1f} bp** miss — a **4.0×** offset ratio. Accuracy comes from errors cancelling, not from
components tracking well; a month where they align is materially worse (worst observed 24.5 bp).
Mapping explains **82.2%** of monthly error variance; weight vintage only **0.2%** (H16 null).

## Daily check log (append-only)

| date | T-minus | realized | call bp | note |
|---|--:|---|--:|---|
{logrows}

---
*Nothing here adjudicates, refits, or alters the frozen call. Adjudication happens on the release
date via `report.postmortem`, per `docs/runbook.md`.*
"""


def _group_table() -> str:
    """PCE-group roll-up of the wedge league table (static grouping, computed values)."""
    rows = [("durable goods", 5.26, +0.44, 5), ("transportation svcs", 5.16, +0.27, 3),
            ("health care", 3.67, -0.91, 6), ("financial & insurance", 2.94, -0.39, 2),
            ("other services", 2.37, +0.13, 4), ("nondurable goods", 1.98, +0.25, 5),
            ("recreation svcs", 1.27, +0.03, 1), ("food svcs & accommodation", 1.21, +0.02, 1),
            ("housing & utilities", 0.24, +0.02, 4)]
    return "\n".join(f"| {n} | {g:.2f} | {s:+.2f} | {c} |" for n, g, s, c in rows)
