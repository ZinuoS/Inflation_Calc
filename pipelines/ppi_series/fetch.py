"""Edge fetcher for ppi_series (Session 2B, Group C) — BLS PPI via the public API.

Final-demand (SA/NSA) + PCE-source industry PPIs from mapping.yaml -> official_current
(methodology replication only, never a backtest target)."""
from __future__ import annotations
import datetime as dt, json, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402
PIPE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]


def series_ids() -> list[str]:
    m = yaml.safe_load((REPO / "mapping" / "mapping.yaml").read_text())["ppi"]
    ids = [e["series_id_sa"] for e in m["final_demand"] if e.get("series_id_sa")]
    ids += [e["series_id_nsa"] for e in m["final_demand"] if e.get("series_id_nsa")]
    ids += [f["series_id"] for f in m["pce_feeders"]]
    return ids


def _seasonal(sid: str, table: dict) -> str:
    for prefix, seas in table.items():
        if sid.startswith(prefix):
            return seas
    return "NSA"


def parse_bls(payload: dict, spec: dict, observed_date: str) -> list[dict]:
    """BLS API JSON -> uniform official_current rows. Pure/testable."""
    rows = []
    for s in payload["Results"]["series"]:
        sid = s["seriesID"]
        seas = _seasonal(sid, spec["seasonal_by_prefix"])
        for pt in s["data"]:
            if not pt["period"].startswith("M") or pt["period"] == "M13":
                continue
            try:
                float(pt["value"])
            except ValueError:
                continue
            rows.append({"source": spec["source"], "series_id": sid, "item_code": sid,
                         "seasonal": seas, "frequency": "monthly",
                         "period": f"{pt['year']}-{pt['period'][1:]}-01", "value": pt["value"]})
    return rows


def fetch(as_of: str | None = None):
    spec = yaml.safe_load((PIPE / "spec.yaml").read_text())
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)
    ids = series_ids()
    api = spec["api"]
    all_rows, prov = [], []
    for i in range(0, len(ids), 25):     # keyless <=25 series/request
        batch = ids[i:i + 25]
        body = json.dumps({"seriesid": batch, "startyear": str(api["startyear"]),
                           "endyear": str(api["endyear"])}).encode()
        raw, status = _ingest.fetch(api["base_url"], headers={"Content-Type": "application/json"},
                                    method_body=body)
        (out / f"ppi_batch_{i}.json").write_bytes(raw)
        prov.append({"label": f"ppi_batch_{i}", "source_url": api["base_url"], "http_status": status,
                     "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "sha256": _ingest.sha256(raw), "bytes": len(raw)})
        all_rows += parse_bls(json.loads(raw), spec, as_of)
    prov_path = _ingest.write_provenance(out, prov)
    staged = out / "staged.csv"
    import csv as _csv
    with open(staged, "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=["source","series_id","item_code","seasonal","frequency","period","value"])
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"ppi: {len(all_rows)} rows, {len({r['series_id'] for r in all_rows})} series")
    return staged, prov_path, as_of


if __name__ == "__main__":
    staged, prov, as_of = fetch(sys.argv[1] if len(sys.argv) > 1 else None)
    from naru.runtime import run as naru_run
    from nowcast.provenance import record_fetch_provenance
    res = naru_run(artifact_path=REPO/"pipelines/official_loader/v1", input_path=staged,
                   db_path=REPO/"data/db/nowcast.sqlite", raw_dir=REPO/"data/db/naru_raw",
                   as_of=dt.date.fromisoformat(as_of))
    record_fetch_provenance(REPO/"data/db/nowcast.sqlite","ppi_series",prov,staged,naru_run_id=res.run_id)
    print(f"ppi: loaded {len(res.row_ids)} rows into official_current")
