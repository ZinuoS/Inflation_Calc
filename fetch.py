"""Edge fetcher for bea_pce_detail (BEA-ingestion session, Task 0).

Pulls BEA NIPA underlying detail via the Data API: Table 2.4.5U (U20405, nominal PCE by
type of product -> the bridge's true weights, RC series codes) and Table 2.4.4U (U20404,
price indexes -> per-component actuals for attribution, RG series codes). Monthly, loaded
into official_current via the shared official_loader naru artifact. Deterministic parse;
API key from env, redacted in provenance (rule 4).
"""
from __future__ import annotations

import csv as _csv
import datetime as dt
import json
import os
import sys
import urllib.parse
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402

PIPE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "db" / "nowcast.sqlite"


def _years(spec: dict) -> list[int]:
    lo, hi = (int(x) for x in spec["api"]["years"].split("-"))
    return list(range(lo, hi + 1))


def _url(spec: dict, table: str, years: list[int], key: str) -> str:
    params = {
        "UserID": key, "method": "GetData", "datasetname": spec["api"]["dataset"],
        "TableName": table, "Frequency": "M", "Year": ",".join(map(str, years)),
        "ResultFormat": "json",
    }
    return spec["api"]["base_url"] + "?" + urllib.parse.urlencode(params)


def _period(tp: str) -> str | None:
    # "2024M12" -> "2024-12-01"
    if "M" not in tp:
        return None
    y, m = tp.split("M")
    return f"{y}-{int(m):02d}-01"


def parse_table(raw: bytes, table: str, spec: dict) -> list[dict]:
    """BEA GetData JSON -> official_current rows. RC (nominal) and RG (price) codes are
    distinct series_ids, so both tables coexist in official_current without collision."""
    d = json.loads(raw)
    res = d["BEAAPI"]["Results"]
    if isinstance(res, dict) and "Error" in res:
        raise SystemExit(f"bea_pce_detail: API error on {table}: {res['Error']}")
    data = res["Data"] if isinstance(res, dict) else res[0]["Data"]
    rows = []
    for r in data:
        val = r["DataValue"].replace(",", "").strip()
        per = _period(r["TimePeriod"])
        if per is None or val in ("", "...", "(NA)", "(D)"):
            continue
        try:
            float(val)
        except ValueError:
            continue
        sid = r["SeriesCode"].strip()
        rows.append({"source": spec["source"], "series_id": sid, "item_code": sid,
                     "seasonal": "SA", "frequency": "monthly", "period": per, "value": val})
    return rows


def fetch(as_of: str | None = None):
    spec = yaml.safe_load((PIPE / "spec.yaml").read_text())
    key = os.environ.get("BEA_API_KEY")
    if not key:
        raise SystemExit("BEA_API_KEY not set in environment (load from .env); refusing to continue.")
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)
    years = _years(spec)
    all_rows, prov = [], []
    for table in spec["api"]["tables"]:
        url = _url(spec, table, years, key)
        raw, status = _ingest.fetch(url, timeout=180)
        (out / f"{table}.json").write_bytes(raw)
        prov.append({"label": table, "source_url": _ingest.redact(url), "http_status": status,
                     "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "sha256": _ingest.sha256(raw), "bytes": len(raw)})
        r = parse_table(raw, table, spec)
        all_rows += r
        print(f"bea_pce_detail: {table} -> {len(r)} rows, {len({x['series_id'] for x in r})} series")
    # dedup by (series_id, period)
    seen, ded = set(), []
    for r in all_rows:
        k = (r["series_id"], r["period"])
        if k not in seen:
            seen.add(k); ded.append(r)
    prov_path = _ingest.write_provenance(out, prov)
    staged = out / "staged.csv"
    with open(staged, "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=["source", "series_id", "item_code", "seasonal", "frequency", "period", "value"])
        w.writeheader()
        for r in ded:
            w.writerow(r)
    print(f"bea_pce_detail: {len(ded)} rows, {len({r['series_id'] for r in ded})} series total")
    return staged, prov_path, as_of


if __name__ == "__main__":
    staged, prov, as_of = fetch(sys.argv[1] if len(sys.argv) > 1 else None)
    from naru.runtime import run as naru_run

    from nowcast.provenance import record_fetch_provenance
    sys.path.insert(0, str(REPO / "pipelines" / "bls_cpi_series"))
    import fetch as bls_fetch  # reuse the O(n^2)-shim indexed-table creator
    bls_fetch.ensure_indexed_official_table(DB)
    res = naru_run(artifact_path=REPO / "pipelines/official_loader/v1", input_path=staged,
                   db_path=DB, raw_dir=REPO / "data/db/naru_raw", as_of=dt.date.fromisoformat(as_of))
    record_fetch_provenance(DB, "bea_pce_detail", prov, staged, naru_run_id=res.run_id)
    print(f"bea_pce_detail: loaded {len(res.row_ids)} rows into official_current")
