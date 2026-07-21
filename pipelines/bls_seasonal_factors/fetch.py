"""Edge fetcher for bls_seasonal_factors (Session 3A, Task 3b reroute).

BLS publishes PROJECTED CPI-U seasonal factors once a year ("Seasonal factors table,
YYYY" XLSX): the factors projected each January and applied mechanically to that year's
first releases. We harvest them so the nowcast can forecast NSA and convert to SA via
NSA / projected_factor = SA, using BLS's own predetermined factor rather than an X-13
re-estimation or a last-year carry-forward.

The XLSX is keyed by item NAME + indent (CPI-U and CPI-W sheets, 12 month columns). The
edge maps names -> item_codes via cu.item, unpivots the 12 months to long form, stamps
published_asof = the Jan-YYYY CPI release date (from release_calendar) as the vintage key,
and emits the uniform long CSV; the naru artifact seasonal_factors_loader/v1 then loads
bls_seasonal_factors keyed by (series_id, reference_period). Rows shown as "-" (indirectly
adjusted aggregates, e.g. Apparel, All items) have no direct factor and are skipped.
"""
from __future__ import annotations

import csv as _csv
import datetime as dt
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402

PIPE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "db" / "nowcast.sqlite"
CU_ITEM = REPO / "data" / "raw" / "bls_cpi_weights" / "2026-07-18" / "cu_item.txt"
MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.",
          "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]


def _norm(s: str) -> str:
    s = re.sub(r"\(\d+\)", "", str(s)).replace("’", "'")
    s = s.replace(",", "").replace(" and ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def _name2code() -> dict[str, str]:
    items = pd.read_csv(CU_ITEM, sep="\t")
    items.columns = [c.strip() for c in items.columns]
    return {_norm(n): c.strip() for n, c in zip(items["item_name"], items["item_code"])}


def _introduced(year: int) -> str:
    """Jan-YYYY CPI release date = when year-YYYY projected factors are introduced."""
    with sqlite3.connect(DB, timeout=30) as conn:
        r = conn.execute(
            "SELECT release_date FROM release_calendar WHERE print='CPI' AND "
            "reference_period=? AND _superseded_by_run_id IS NULL", (f"{year}-01-01",)
        ).fetchone()
    if not r:
        raise SystemExit(f"bls_seasonal_factors: no Jan-{year} CPI release date in release_calendar")
    return r[0]


def parse_factor_file(xlsx_path: Path, year: int, name2code: dict[str, str]) -> list[dict]:
    """CPI-U projected factors -> long rows. Deterministic, pure (given name2code +
    introduced date), unit-testable against a golden raw sample."""
    intro = _introduced(year)
    df = pd.read_excel(xlsx_path, sheet_name="CPI-U", header=None)
    # locate the month-header row (the row whose cells contain 'Jan.' .. 'Dec.')
    hdr = next(i for i in range(len(df)) if list(df.iloc[i, 2:14].values)[:1] == ["Jan."])
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for i in range(hdr + 1, len(df)):
        name = df.iat[i, 1]
        if not isinstance(name, str) or not name.strip():
            continue
        code = name2code.get(_norm(name))
        if code is None:
            continue
        vals = df.iloc[i, 2:14].tolist()
        if not all(isinstance(v, (int, float)) and pd.notna(v) for v in vals):
            continue  # "-" (indirectly adjusted) or partial row
        for mi, v in enumerate(vals):
            ref = f"{year}-{mi + 1:02d}-01"
            key = (f"CUSR0000{code}", ref)
            if key in seen:   # first occurrence wins (guards duplicate display names)
                continue
            seen.add(key)
            rows.append({"series_id": f"CUSR0000{code}", "item_code": code,
                         "reference_period": ref, "projected_factor": f"{v / 100:.6f}",
                         "factor_year": str(year), "published_asof": intro})
    return rows


def fetch(as_of: str | None = None):
    spec = yaml.safe_load((PIPE / "spec.yaml").read_text())
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)
    name2code = _name2code()
    all_rows, prov = [], []
    for year in spec["years"]:
        url = spec["url_template"].format(year=year)
        try:
            raw, status = _ingest.fetch(url, timeout=60)
        except Exception as e:
            print(f"bls_seasonal_factors: {year} fetch failed ({e}); skipping")
            continue
        if raw[:2] != b"PK":  # BLS "Access Denied" HTML instead of an XLSX
            print(f"bls_seasonal_factors: {year} did not return an xlsx (blocked?); skipping")
            continue
        xp = out / f"seasonal-factors-{year}.xlsx"
        xp.write_bytes(raw)
        prov.append({"label": f"seasonal_factors_{year}", "source_url": url, "http_status": status,
                     "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "sha256": _ingest.sha256(raw), "bytes": len(raw)})
        yr = parse_factor_file(xp, year, name2code)
        all_rows += yr
        print(f"bls_seasonal_factors: {year} -> {len(yr)} factor rows "
              f"({len(yr) // 12} directly-adjusted items)")
    prov_path = _ingest.write_provenance(out, prov)
    staged = out / spec["paths"]["staged_csv"]
    cols = spec["output_csv_columns"]
    with open(staged, "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"bls_seasonal_factors: {len(all_rows)} rows across {len(prov)} factor files")
    return staged, prov_path, as_of


if __name__ == "__main__":
    staged, prov, as_of = fetch(sys.argv[1] if len(sys.argv) > 1 else None)
    from naru.runtime import run as naru_run

    from nowcast.provenance import record_fetch_provenance
    res = naru_run(artifact_path=REPO / "pipelines/seasonal_factors_loader/v1", input_path=staged,
                   db_path=DB, raw_dir=REPO / "data/db/naru_raw", as_of=dt.date.fromisoformat(as_of))
    record_fetch_provenance(DB, "bls_seasonal_factors", prov, staged, naru_run_id=res.run_id)
    print(f"bls_seasonal_factors: loaded {len(res.row_ids)} rows into bls_seasonal_factors")
