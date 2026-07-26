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


# ---------------------------------------------------------------------------
# Forward vintage capture (Task 3) — for `revised_latest_only` sources.
#
# A source that restates its own history cannot be backtested honestly from the
# latest snapshot: the value we would have SEEN at a past forecast time is gone.
# BLS/Zillow/Apartment List publish no vintage archive, so the only way to get a
# leakage-free history is to build our own going forward. Every pull of such a
# source archives the FULL downloaded history under
#   data/raw/{source}/vintage_{YYYY-MM-DD}/
# with a manifest. Snapshots are IMMUTABLE: an existing vintage directory is never
# overwritten or mutated (asserted by tests/test_vintage_capture.py). This is what
# makes H14 (ATRR rent carry) re-runnable on our own archive in ~4 quarters.
# ---------------------------------------------------------------------------

VINTAGE_MANIFEST = "manifest.json"


class VintageExists(Exception):
    """A vintage snapshot for this (source, date) already exists — never overwritten."""


def vintage_dir(source: str, as_of: str) -> Path:
    return REPO / "data" / "raw" / source / f"vintage_{as_of}"


def archive_vintage(source: str, as_of: str, payload: bytes, filename: str,
                    url: str, rows: int | None = None,
                    period_min: str | None = None, period_max: str | None = None,
                    extra: dict | None = None) -> Path:
    """Archive one immutable full-history snapshot. Raises VintageExists if already captured.

    Idempotent-by-refusal: re-running a pull on the same day does not silently replace the
    snapshot, because a replaced snapshot would destroy exactly the point-in-time evidence the
    archive exists to preserve.
    """
    d = vintage_dir(source, as_of)
    if d.exists() and (d / VINTAGE_MANIFEST).exists():
        raise VintageExists(f"{d.relative_to(REPO)} already captured; snapshots are immutable")
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_bytes(payload)
    manifest = {
        "source": source, "vintage_date": as_of, "filename": filename, "source_url": url,
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sha256": sha256(payload), "bytes": len(payload),
        "rows": rows, "period_min": period_min, "period_max": period_max,
        "vintage_status": "revised_latest_only",
        "why": ("source restates its own history and publishes no vintage archive; this snapshot "
                "is the point-in-time record we could not otherwise recover"),
        **(extra or {}),
    }
    (d / VINTAGE_MANIFEST).write_text(json.dumps(manifest, indent=2))
    return d


def list_vintages(source: str) -> list[str]:
    """Captured vintage dates for a source, ascending."""
    base = REPO / "data" / "raw" / source
    if not base.exists():
        return []
    return sorted(p.name.replace("vintage_", "") for p in base.iterdir()
                  if p.is_dir() and p.name.startswith("vintage_")
                  and (p / VINTAGE_MANIFEST).exists())
