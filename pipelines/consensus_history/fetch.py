"""consensus_history (Session 8) — press-reported consensus median per print.

MANUAL-CURATION artifact, by necessity. The automated fetch channel is BLOCKED: WebFetch returns
HTTP 403 on every news outlet (CNBC, Morningstar, CEPR, ...), and the search-snippet summarizer
conflates actual-vs-expected across outlets — which fails the no-fabrication bar for a table of
CITED facts. Per CLAUDE.md rule 5 a blocked source is not fought.

So consensus rows are added ONLY when a human opens the dated article and reads the figure. Each
row is one fact: (print, reference_month, variable, consensus_pct, source_url, article_date,
article_type, retrieved_at). Where preview and recap disagree, prefer the PRE-print article and
record both (two rows, article_type=preview kept as canonical). A month with no verifiable
consensus is a GAP row (consensus_pct blank, note explaining) — NEVER interpolated.

This module (a) defines the schema, (b) seeds the full 2023-01..present grid as gap rows for the
tracked prints, and (c) validates any curated CSV against the schema. It performs NO network I/O —
curation happens out-of-band and is pasted into data/benchmarks/consensus_history.csv.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_CSV = REPO / "data" / "benchmarks" / "consensus_history.csv"
COLS = ["print", "reference_month", "variable", "consensus_pct", "article_type",
        "source_url", "article_date", "retrieved_at", "note"]
# variable = mom_headline | mom_core | yoy_headline | yoy_core ; consensus is the rounded market median.
TRACKED = {"CPI": ["mom_headline", "mom_core"], "PCE": ["mom_core"], "PPI": ["mom_headline"]}
ARTICLE_TYPES = {"preview", "recap", "gap"}


def month_grid(start: str = "2023-01-01", end: str | None = None) -> list[str]:
    end = end or dt.date.today().replace(day=1).isoformat()
    out, m = [], dt.date.fromisoformat(start)
    last = dt.date.fromisoformat(end)
    while m <= last:
        out.append(m.isoformat())
        m = dt.date(m.year + (m.month // 12), (m.month % 12) + 1, 1)
    return out


def seed_gap_grid(path: Path = OUT_CSV) -> int:
    """Write the full tracked grid as gap rows IF no curated file exists yet. Idempotent: never
    overwrites a file that already contains curated (non-gap) rows."""
    if path.exists():
        existing = read_rows(path)
        if any(r["article_type"] != "gap" for r in existing):
            return 0                                   # curated data present: do not clobber
    rows = []
    for m in month_grid():
        for prnt, variables in TRACKED.items():
            for var in variables:
                rows.append({"print": prnt, "reference_month": m, "variable": var,
                             "consensus_pct": "", "article_type": "gap", "source_url": "",
                             "article_date": "", "retrieved_at": "",
                             "note": "awaiting manual curation (auto-backfill 403-blocked)"})
    write_rows(rows, path)
    return len(rows)


def read_rows(path: Path = OUT_CSV) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def write_rows(rows: list[dict], path: Path = OUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows([{c: r.get(c, "") for c in COLS} for r in rows])


def validate(rows: list[dict]) -> list[str]:
    """Schema + provenance integrity. A curated (non-gap) row MUST carry a value, a source_url and
    an article_date; a gap row MUST NOT carry a value. Returns a list of problems (empty = ok)."""
    problems = []
    for i, r in enumerate(rows):
        tag = f"row {i} ({r.get('print')} {r.get('reference_month')} {r.get('variable')})"
        if r.get("article_type") not in ARTICLE_TYPES:
            problems.append(f"{tag}: bad article_type {r.get('article_type')!r}")
        curated = r.get("article_type") in ("preview", "recap")
        has_val = r.get("consensus_pct", "") != ""
        if curated and not has_val:
            problems.append(f"{tag}: curated row with no consensus_pct")
        if curated and not (r.get("source_url") and r.get("article_date")):
            problems.append(f"{tag}: curated row missing source_url/article_date (uncited fact)")
        if not curated and has_val:
            problems.append(f"{tag}: gap row carries a value (interpolation smell)")
        if has_val:
            try:
                float(r["consensus_pct"])
            except ValueError:
                problems.append(f"{tag}: consensus_pct not numeric")
    return problems


def coverage() -> dict:
    rows = read_rows()
    grid = {(r["print"], r["reference_month"], r["variable"]) for r in rows}
    curated = {k for k in grid if any(
        r["article_type"] in ("preview", "recap") and r["consensus_pct"] != ""
        and (r["print"], r["reference_month"], r["variable"]) == k for r in rows)}
    return {"total_slots": len(grid), "curated": len(curated), "gap": len(grid) - len(curated)}


if __name__ == "__main__":
    n = seed_gap_grid()
    print(f"consensus_history: seeded {n} gap rows" if n else "consensus_history: curated file present, not reseeded")
    probs = validate(read_rows())
    print("validation:", "OK" if not probs else f"{len(probs)} problems")
    print("coverage:", coverage())
