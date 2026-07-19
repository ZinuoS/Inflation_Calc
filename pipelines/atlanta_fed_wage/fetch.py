"""Edge fetcher for atlanta_fed_wage (Session 2B, Group A) — Atlanta Fed Wage
Growth Tracker via FRED. MONITOR source (wage-growth rate, not a price proxy)."""
from __future__ import annotations
import datetime as dt, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402
PIPE = Path(__file__).resolve().parent

def to_staged(observations, spec, observed_date):
    """FRED monthly (date,value) -> uniform staged rows. Pure/testable."""
    return [{"source": spec["source"], "series_key": spec["series_key"],
             "frequency": spec["frequency"], "period": date, "value": value,
             "vintage_status": spec["vintage_status"], "observed_date": observed_date}
            for date, value in observations]

def fetch(as_of=None):
    spec = yaml.safe_load((PIPE/"spec.yaml").read_text())
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)
    raw, status, url, obs = _ingest.fred_series(spec["fred_series_id"])
    (out/f"{spec['fred_series_id']}.json").write_bytes(raw)
    prov=[{"label":spec["fred_series_id"],"source_url":url,"http_status":status,
           "retrieved_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
           "sha256":_ingest.sha256(raw),"bytes":len(raw)}]
    prov_path=_ingest.write_provenance(out,prov)
    rows=to_staged(obs, spec, observed_date=as_of)   # revised_latest_only -> pull date
    staged=out/"staged.csv"; _ingest.write_staged_csv(staged,rows)
    print(f"atlanta_fed_wage: {len(rows)} monthly rows {rows[0]['period']}..{rows[-1]['period']}")
    n=_ingest.load(spec["source"], staged, prov_path, as_of)
    print(f"atlanta_fed_wage: loaded {n} rows")
    return staged

if __name__ == "__main__":
    fetch(sys.argv[1] if len(sys.argv)>1 else None)
