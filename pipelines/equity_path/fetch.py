"""Edge fetcher for equity_path (Session 3B, Task 1) — S&P 500 daily via FRED.

Daily closes stored as-is; monthly alignment (average) is alignment.py's job. Feeds the
PCE-bridge equity path for portfolio-management (PPI discontinued 2022-12) and the
equity-linked part of imputed financial services. Only a derived MoM relative is used.
"""
from __future__ import annotations
import datetime as dt, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402
PIPE = Path(__file__).resolve().parent


def to_staged(obs, spec):
    return [{"source": spec["source"], "series_key": spec["series_key"],
             "frequency": spec["frequency"], "period": d, "value": v,
             "vintage_status": spec["vintage_status"], "observed_date": d} for d, v in obs]


def fetch(as_of: str | None = None) -> Path:
    spec = yaml.safe_load((PIPE / "spec.yaml").read_text())
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)
    raw, status, url, obs = _ingest.fred_series(spec["fred_series_id"])
    (out / f"{spec['fred_series_id']}.json").write_bytes(raw)
    prov = [{"label": spec["fred_series_id"], "source_url": url, "http_status": status,
             "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
             "sha256": _ingest.sha256(raw), "bytes": len(raw)}]
    prov_path = _ingest.write_provenance(out, prov)
    rows = to_staged(obs, spec)
    staged = out / "staged.csv"
    _ingest.write_staged_csv(staged, rows)
    n = _ingest.load(spec["source"], staged, prov_path, as_of)
    print(f"equity_path(sp500): {len(rows)} daily rows {rows[0]['period']}..{rows[-1]['period']}; loaded {n}")
    return staged


if __name__ == "__main__":
    fetch(sys.argv[1] if len(sys.argv) > 1 else None)
