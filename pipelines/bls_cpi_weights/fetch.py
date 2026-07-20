"""Edge fetcher for bls_cpi_weights (Session 3A, Task 2) — vintaged CPI relative importances.

BLS publishes an annual relative-importance table ({year}.xlsx, "December {year}");
weight_year = {year} = the calendar year those weights are in effect (BLS updates
weights annually). We ingest each available year so src/nowcast/weights.py can serve
weights AS OF a date (a 2021 backtest sees 2021 weights). The xlsx is multi-sheet
(naru#4); the edge parses Table 1 into the uniform CSV, then naru loads cpi_weights.
"""
from __future__ import annotations
import datetime as dt
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402

PIPE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
CU_ITEM = REPO / "data" / "raw" / "bls_cpi_weights" / "2026-07-18" / "cu_item.txt"

ALIASES = {  # RI-table wording -> cu.item wording (same as the Session-1 generator)
    "Housing at school, excluding board": "Lodging while at school",
    "Technical and business school tuition and fees": "Technical and vocational school tuition and fixed fees",
}


def _norm(s: str) -> str:
    s = re.sub(r"\(\d+\)", "", str(s)).replace("’", "'")
    s = s.replace(",", "").replace(" and ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def _name2code() -> dict[str, str]:
    items = pd.read_csv(CU_ITEM, sep="\t")
    items.columns = [c.strip() for c in items.columns]
    return {_norm(n): c.strip() for n, c in zip(items["item_name"], items["item_code"])}


def parse_table1(xlsx_path: Path, weight_year: int, name2code: dict[str, str]) -> list[dict]:
    """RI Table 1 -> [{weight_year, item_code, weight_cpi_u, weight_cpi_w}]. The
    expenditure-category panel only (stop at 'Special aggregate indexes' to avoid the
    duplicate special-aggregate rows). 'All items' -> SA0. Deterministic. Pure/testable."""
    df = pd.read_excel(xlsx_path, sheet_name="Table 1", header=None)
    df.columns = ["indent", "item", "cpi_u", "cpi_w"] + list(df.columns[4:])
    rows, in_panel = [], False
    for _, r in df.iterrows():
        name = str(r["item"]).strip() if pd.notna(r["item"]) else ""
        if name == "Expenditure category":
            in_panel = True
            continue
        if name == "Special aggregate indexes":
            break
        if not in_panel or not name or pd.isna(r["cpi_u"]):
            continue
        code = "SA0" if name == "All items" else name2code.get(_norm(ALIASES.get(name, name)))
        if code is None:
            continue
        rows.append({"weight_year": str(weight_year), "item_code": code,
                     "weight_cpi_u": f"{float(r['cpi_u']):.3f}",
                     "weight_cpi_w": f"{float(r['cpi_w']):.3f}" if pd.notna(r["cpi_w"]) else "0.000"})
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
            print(f"bls_cpi_weights: {year} fetch failed ({e}); skipping")
            continue
        xp = out / f"{year}.xlsx"
        xp.write_bytes(raw)
        prov.append({"label": f"relative_importance_{year}", "source_url": url, "http_status": status,
                     "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "sha256": _ingest.sha256(raw), "bytes": len(raw)})
        yr_rows = parse_table1(xp, year, name2code)
        all_rows += yr_rows
        print(f"bls_cpi_weights: {year} -> {len(yr_rows)} weighted item rows")
    prov_path = _ingest.write_provenance(out, prov)
    import csv as _csv
    staged = out / "staged.csv"
    with open(staged, "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=["weight_year", "item_code", "weight_cpi_u", "weight_cpi_w"])
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"bls_cpi_weights: {len(all_rows)} rows across {len(spec['years'])} years")
    return staged, prov_path, as_of


if __name__ == "__main__":
    staged, prov, as_of = fetch(sys.argv[1] if len(sys.argv) > 1 else None)
    from naru.runtime import run as naru_run
    from nowcast.provenance import record_fetch_provenance
    res = naru_run(artifact_path=REPO / "pipelines/cpi_weights_loader/v1", input_path=staged,
                   db_path=REPO / "data/db/nowcast.sqlite", raw_dir=REPO / "data/db/naru_raw",
                   as_of=dt.date.fromisoformat(as_of))
    record_fetch_provenance(REPO / "data/db/nowcast.sqlite", "bls_cpi_weights", prov, staged, naru_run_id=res.run_id)
    print(f"bls_cpi_weights: loaded {len(res.row_ids)} rows into cpi_weights")
