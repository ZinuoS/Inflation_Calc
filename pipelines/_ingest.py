"""Shared edge-driver helpers for proxy ingestion (Session 2B).

Network lives ONLY in pipelines/ (CLAUDE.md rule 4); this module is imported by
each source's fetch.py. Each source normalizes its messy raw pull into the uniform
proxy staged-CSV contract (columns below), which the shared naru artifact
pipelines/proxy_loader/v1 loads into the governed proxy_observations table with
lineage. Per-source distinctness (license, deterministic parse, provenance, golden
raw sample + parse test) lives in each source folder; only the trivial uniform
CSV->DB load is shared. Provenance (url, retrieved_at, sha256) is recorded via
nowcast.provenance (naru#2 shim).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROXY_LOADER = REPO / "pipelines" / "proxy_loader" / "v1"
DB = REPO / "data" / "db" / "nowcast.sqlite"
NARU_RAW = REPO / "data" / "db" / "naru_raw"
UA = "inflation-nowcast-research/0.1 (proxy-ingest; contact zinuoashley@gmail.com)"

STAGED_COLUMNS = [
    "source",            # e.g. zori, eia_gasoline
    "series_key",        # sub-series (region, drug ndc, "US")
    "frequency",         # weekly | monthly
    "period",            # observation period, first-of-month YYYY-MM-01 (monthly)
    "value",             # numeric
    "vintage_status",    # point_in_time | unrevised | revised_latest_only
    "observed_date",     # publication date (point_in_time) or pull date (revised)
]


def fetch(url: str, headers: dict | None = None, timeout: int = 90,
          method_body: bytes | None = None) -> tuple[bytes, int]:
    """GET, or POST when method_body is given (e.g. the BLS API batch endpoint)."""
    req = urllib.request.Request(
        url, data=method_body, headers={"User-Agent": UA, **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.status


def redact(url: str) -> str:
    parts = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(parts.query)
    for k in ("api_key", "apikey", "key"):
        if k in q:
            q[k] = ["REDACTED"]
    return urllib.parse.urlunparse(parts._replace(query=urllib.parse.urlencode(q, doseq=True)))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fred_series(series_id: str, start: str = "1900-01-01") -> tuple[bytes, int, str, list[tuple[str, str]]]:
    """Fetch a FRED series' CURRENT observations (proxy delivery channel for EIA
    etc.). Returns (raw_bytes, status, redacted_url, [(date, value), ...]). Not a
    vintage pull -- FRED redistributes the published series. API key from env."""
    import os

    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise SystemExit("FRED_API_KEY not set in environment (load from .env)")
    params = {
        "series_id": series_id, "api_key": key, "file_type": "json",
        "observation_start": start,
    }
    url = "https://api.stlouisfed.org/fred/series/observations?" + urllib.parse.urlencode(params)
    raw, status = fetch(url)
    obs = json.loads(raw)["observations"]
    return raw, status, redact(url), [(o["date"], o["value"]) for o in obs if o["value"] != "."]


def raw_dir(source: str, as_of: str) -> Path:
    d = REPO / "data" / "raw" / source / as_of
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_staged_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=STAGED_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in STAGED_COLUMNS})


def write_provenance(out_dir: Path, records: list[dict]) -> Path:
    p = out_dir / "provenance.json"
    p.write_text(json.dumps(records, indent=2))
    return p


def load(source: str, staged_csv: Path, provenance_json: Path, as_of: str) -> int:
    """Run the shared proxy_loader naru artifact on a source's staged CSV, then
    record fetch provenance. Returns rows loaded. Imports naru/nowcast lazily so
    this module stays import-light for parse-only tests."""
    from naru.runtime import run as naru_run

    from nowcast.provenance import record_fetch_provenance

    result = naru_run(
        artifact_path=PROXY_LOADER,
        input_path=staged_csv,
        db_path=DB,
        raw_dir=NARU_RAW,
        as_of=dt.date.fromisoformat(as_of),
    )
    record_fetch_provenance(DB, source, provenance_json, staged_csv, naru_run_id=result.run_id)
    return len(result.row_ids)
