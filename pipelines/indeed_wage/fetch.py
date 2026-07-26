"""Edge fetcher for indeed_wage (Session 2B, Group A) — Indeed Wage Tracker.
MONITOR source (posted wage-growth YoY rate, US)."""
from __future__ import annotations
import csv, datetime as dt, io, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402
PIPE = Path(__file__).resolve().parent

def parse(raw_bytes, spec, observed_date):
    """Indeed long CSV -> uniform staged rows for US. Pure/testable."""
    p = spec["parse"]
    r = csv.DictReader(io.StringIO(raw_bytes.decode("utf-8")))
    rows = []
    for rec in r:
        if rec[p["filter_col"]] != p["filter_value"]:
            continue
        val = rec[p["value_col"]]
        if val in ("", "NA"):
            continue
        period = dt.datetime.strptime(rec[p["month_col"]], p["month_format"]).date().replace(day=1).isoformat()
        rows.append({"source": spec["source"], "series_key": spec["series_key"],
                     "frequency": p["frequency"], "period": period, "value": val,
                     "vintage_status": spec["vintage_status"], "observed_date": observed_date})
    return rows

def fetch(as_of=None):
    spec = yaml.safe_load((PIPE/"spec.yaml").read_text())
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)
    raw, status = _ingest.fetch(spec["url"])
    (out/"posted-wage-growth-by-country.csv").write_bytes(raw)
    # Task 3 — forward vintage capture: this source restates its own history and
    # publishes no vintage archive, so every pull archives an immutable full-history
    # snapshot. Re-running the same day raises VintageExists rather than overwriting.
    try:
        v = _ingest.archive_vintage(spec["source"], as_of, raw, "posted-wage-growth-by-country.csv",
                                    spec["url"])
        print(f"vintage captured: {v.name}")
    except _ingest.VintageExists as e:
        print(f"vintage already captured today ({e}); not overwritten")
    prov=[{"label":"indeed_posted_wage_growth","source_url":spec["url"],"http_status":status,
           "retrieved_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
           "sha256":_ingest.sha256(raw),"bytes":len(raw)}]
    prov_path=_ingest.write_provenance(out,prov)
    rows=parse(raw, spec, observed_date=as_of)
    staged=out/"staged.csv"; _ingest.write_staged_csv(staged,rows)
    print(f"indeed_wage: {len(rows)} monthly US rows {rows[0]['period']}..{rows[-1]['period']}")
    n=_ingest.load(spec["source"], staged, prov_path, as_of)
    print(f"indeed_wage: loaded {n} rows")
    return staged

if __name__ == "__main__":
    fetch(sys.argv[1] if len(sys.argv)>1 else None)
