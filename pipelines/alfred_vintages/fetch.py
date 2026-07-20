"""Edge fetcher for alfred_vintages (Session 2A, Task 2).

One FRED observations call per series with a full realtime span returns every
observation tagged with its vintage window [realtime_start, realtime_end). The
ONLY network step (rule 4). Writes immutable raw JSON per series, provenance.json,
and one stacked canonical CSV the naru artifact in v1/ loads deterministically.

observed_asof_vintage = realtime_start (the vintage date the value became current).
first release = the row with the earliest observed_asof_vintage per (series,
reference_period) -- materialized as a view after load.

API key from env FRED_API_KEY; never hardcoded, never written to disk.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
PIPE = Path(__file__).resolve().parent
UA = "inflation-nowcast-research/0.1 (alfred_vintages; contact zinuoashley@gmail.com)"


def _redact(url: str) -> str:
    parts = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(parts.query)
    if "api_key" in q:
        q["api_key"] = ["REDACTED"]
    return urllib.parse.urlunparse(parts._replace(query=urllib.parse.urlencode(q, doseq=True)))


def _fetch_json(url: str) -> tuple[bytes, int]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read(), resp.status


def fetch(as_of: str | None = None, only: set[str] | None = None) -> Path:
    """Fetch ALFRED vintages. `only` (a set of alfred_ids) restricts the pull to a
    subset -- used for incremental Session-2B adds so existing series are not
    re-superseded. Default (None) fetches every series in spec.yaml."""
    spec = yaml.safe_load((PIPE / "spec.yaml").read_text())
    if only is not None:
        spec = {**spec, "series": [s for s in spec["series"] if s["alfred_id"] in only]}
    api = spec["api"]
    key = os.environ.get("FRED_API_KEY")
    if not key:
        sys.exit("FRED_API_KEY not set in environment (load from .env); refusing to continue.")

    stamp = as_of or dt.date.today().isoformat()
    out_dir = REPO / spec["paths"]["raw_dir"] / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()

    provenance: list[dict] = []
    rows: list[dict] = []

    for entry in spec["series"]:
        series_id = entry["alfred_id"]
        # Fall back to the series' own id when there is no CPI/PPI crosswalk (PCE
        # headline/core are targets, not CPI items) -- keeps the column non-null
        # and unambiguous ("maps to itself").
        mapping_series_id = entry.get("mapping_series_id") or series_id
        params = {
            "series_id": series_id,
            "api_key": key,
            "file_type": api["file_type"],
            "realtime_start": api["realtime_start"],
            "realtime_end": api["realtime_end"],
        }
        url = api["base_url"] + "?" + urllib.parse.urlencode(params)
        raw, status = _fetch_json(url)
        (out_dir / f"{series_id}.json").write_bytes(raw)
        provenance.append({
            "label": series_id,
            "role": entry.get("role"),
            "source_url": _redact(url),
            "http_status": status,
            "retrieved_at_utc": retrieved_at,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        })
        for o in json.loads(raw)["observations"]:
            # ALFRED reports a missing observation as "." (the value did not exist
            # for that reference period at that vintage). Such rows carry no
            # information -- drop them; first-release is the earliest vintage that
            # actually has a value.
            if o["value"] == ".":
                continue
            rows.append({
                "series_id": series_id,
                "mapping_series_id": mapping_series_id,
                "reference_period": o["date"],
                "observed_asof_vintage": o["realtime_start"],
                "vintage_end": o["realtime_end"],
                "value": o["value"],
            })

    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2))
    rows.sort(key=lambda r: (r["series_id"], r["reference_period"], r["observed_asof_vintage"]))
    csv_path = out_dir / spec["paths"]["staged_csv"]
    _write_csv(csv_path, spec["output_csv_columns"], rows)
    _summary(spec, rows, csv_path, out_dir)
    return csv_path


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    import csv
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in columns})


def _summary(spec, rows, csv_path, out_dir) -> None:
    from collections import Counter
    per_series = Counter(r["series_id"] for r in rows)
    print(f"raw + normalized -> {out_dir}")
    print(f"  series: {len(spec['series'])}  total vintage rows: {len(rows)}")
    for sid, n in sorted(per_series.items()):
        refs = [r["reference_period"] for r in rows if r["series_id"] == sid]
        print(f"    {sid:16s} rows={n:5d}  ref {min(refs)}..{max(refs)}")
    print(f"  canonical CSV: {csv_path}")


if __name__ == "__main__":
    fetch(as_of=sys.argv[1] if len(sys.argv) > 1 else None)
