"""Pristine forward ledger (Session 6, Task 3). APPEND-ONLY.

docs/pristine_ledger.md holds one row per forward call. Two operations are legal:
  1. **append** a new call, and
  2. **populate** the realized/deviation/verdict of an existing row once its print lands.
Anything else — editing a call, a band, an as-of, deleting a row — is a **test failure**: each
row carries a `row_hash` over its immutable fields (instrument, ref_month, as_of, frozen,
call_bp, band_bp), so a retroactive edit cannot pass `test_ledger`.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "docs" / "pristine_ledger.md"
COLS = ["n", "instrument", "ref_month", "as_of", "frozen", "call_bp", "band_bp",
        "consensus_bp", "consensus_asof", "realized_bp", "deviation_bp", "verdict", "row_hash"]
IMMUTABLE = ["instrument", "ref_month", "as_of", "frozen", "call_bp", "band_bp"]
PENDING = "—"

HEADER = """# Pristine forward ledger

**Append-only.** One row per forward call, written when the call is made — before the print.
Legal edits: (1) append a new row, (2) populate `consensus_bp` / `consensus_asof` when the preview
articles land (after our T-4 freeze, before the print), (3) populate `realized_bp` / `deviation_bp`
/ `verdict` once the print lands. Any other change breaks the row's `row_hash` and fails
`tests/test_ledger.py`.

`call_bp` = predicted first-release MoM (NSA for CPI, core PCE for PCE). `band_bp` = the OOS band
at that lead. `consensus_bp` = press consensus median, carrying its OWN as-of (it closes later than
our freeze). `frozen` = whether the call was past its T-4 freeze. Misses are kept, never edited out.

"""


def row_hash(row: dict) -> str:
    return hashlib.sha256("|".join(str(row[k]) for k in IMMUTABLE).encode()).hexdigest()[:12]


def read_rows() -> list[dict]:
    if not LEDGER.exists():
        return []
    rows = []
    for line in LEDGER.read_text().splitlines():
        if not line.startswith("|") or line.startswith("| n ") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == len(COLS):
            rows.append(dict(zip(COLS, cells)))
    return rows


def _write(rows: list[dict]) -> None:
    out = [HEADER, "| " + " | ".join(COLS) + " |", "|" + "|".join(["---"] * len(COLS)) + "|"]
    out += ["| " + " | ".join(str(r[c]) for c in COLS) + " |" for r in rows]
    LEDGER.write_text("\n".join(out) + "\n")


def _freeze_kind(row: dict) -> str:
    """Dedup dimension distinguishing the pre-freeze (T-21…) call from the T-3 frozen call for the
    same (instrument, ref_month). Derived from the `frozen` flag — no stored column, no hash change
    (the hash already covers as_of + frozen, which differ between the two rows)."""
    frozen = row.get("frozen")
    return "frozen" if (frozen is True or frozen == "yes") else "prefreeze"


def append_call(rec: dict) -> dict:
    rows = read_rows()
    kind = _freeze_kind(rec)
    if any(r["instrument"] == rec["instrument"] and r["ref_month"] == rec["ref_month"]
           and _freeze_kind(r) == kind for r in rows):
        return {"skipped": f"row already exists (append-only: one {kind} call per instrument/month)"}
    row = {"n": str(len(rows) + 1), "instrument": rec["instrument"], "ref_month": rec["ref_month"],
           "as_of": rec["as_of"], "frozen": "yes" if rec.get("frozen") else "no",
           "call_bp": f"{rec['call_bp']:+.1f}", "band_bp": f"{rec['band_bp']:.1f}",
           "consensus_bp": PENDING, "consensus_asof": PENDING,
           "realized_bp": PENDING, "deviation_bp": PENDING, "verdict": PENDING}
    row["row_hash"] = row_hash(row)
    rows.append(row)
    _write(rows)
    return row


def find_row(instrument: str, ref_month: str) -> dict | None:
    return next((r for r in read_rows() if r["instrument"] == instrument and r["ref_month"] == ref_month), None)


def populate_realized(instrument: str, ref_month: str, realized_bp: float, deviation_bp: float,
                      verdict: str) -> dict | None:
    rows = read_rows()
    for r in rows:
        if r["instrument"] == instrument and r["ref_month"] == ref_month:
            if r["realized_bp"] != PENDING:
                return {"skipped": "already populated (append-only)"}
            r["realized_bp"] = f"{realized_bp:+.1f}"
            r["deviation_bp"] = f"{deviation_bp:+.1f}"
            r["verdict"] = verdict
            _write(rows)          # row_hash unchanged: it covers immutable fields only
            return r
    return None


def populate_consensus(instrument: str, ref_month: str, consensus_bp: float, consensus_asof: str) -> dict | None:
    """Record the press consensus for an existing call. Consensus lands AFTER our T-4 freeze but
    BEFORE the print (preview articles ~T-1 to T-3), so it carries its OWN as-of. Non-immutable:
    populated once, does not touch the row_hash. Idempotent (won't overwrite a set consensus)."""
    rows = read_rows()
    for r in rows:
        if r["instrument"] == instrument and r["ref_month"] == ref_month:
            if r.get("consensus_bp", PENDING) != PENDING:
                return {"skipped": "consensus already populated (append-only)"}
            r["consensus_bp"] = f"{consensus_bp:+.1f}"
            r["consensus_asof"] = consensus_asof
            _write(rows)                 # row_hash unchanged: consensus is not an immutable field
            return r
    return None


def verify() -> list[str]:
    """Return a list of integrity problems (empty = ledger intact)."""
    problems = []
    for r in read_rows():
        if row_hash(r) != r["row_hash"]:
            problems.append(f"row {r['n']} ({r['instrument']} {r['ref_month']}): immutable fields "
                            f"edited — hash {r['row_hash']} != {row_hash(r)}")
    return problems
