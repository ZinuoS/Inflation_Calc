"""Edge fetcher for release_calendar (Session 2A, Task 1).

The ONLY network step for this pipeline (CLAUDE.md rule 4). It:
  1. GETs fred/release/dates for each release in spec.yaml,
  2. writes the immutable raw JSON per print to data/raw/release_calendar/{date}/,
  3. writes provenance.json (url with api_key REDACTED, retrieved_at, sha256, bytes),
  4. normalizes to a canonical CSV (one first-release row per print x reference
     month; collisions/gaps logged to exceptions.json), which the naru artifact
     in v1/ then loads deterministically.

The naru artifact is pure/offline; all messiness (network, dedup, mapping) is
resolved here at the edge and frozen into the CSV + JSON on disk. Rerunning naru
against the same CSV is byte-deterministic.

API key: read from env FRED_API_KEY. Never hardcoded, never written to disk.
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
UA = "inflation-nowcast-research/0.1 (release_calendar; contact zinuoashley@gmail.com)"


def _load_spec() -> dict:
    return yaml.safe_load((PIPE / "spec.yaml").read_text())


def _reference_month(d: dt.date) -> dt.date:
    """A print released in calendar month X covers reference month X-1."""
    return dt.date(d.year - 1, 12, 1) if d.month == 1 else dt.date(d.year, d.month - 1, 1)


def _redact(url: str) -> str:
    parts = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(parts.query)
    if "api_key" in q:
        q["api_key"] = ["REDACTED"]
    redacted = urllib.parse.urlencode(q, doseq=True)
    return urllib.parse.urlunparse(parts._replace(query=redacted))


def _fetch_json(url: str) -> tuple[bytes, int]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read(), resp.status


def fetch(as_of: str | None = None) -> Path:
    spec = _load_spec()
    api = spec["api"]
    key = os.environ.get("FRED_API_KEY")
    if not key:
        sys.exit("FRED_API_KEY not set in environment (load from .env); refusing to continue.")

    stamp = as_of or dt.date.today().isoformat()
    out_dir = REPO / spec["paths"]["raw_dir"] / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    provenance: list[dict] = []
    per_print_dates: dict[str, list[str]] = {}

    for print_label, release_id in spec["releases"].items():
        params = {
            "release_id": release_id,
            "api_key": key,
            "file_type": api["file_type"],
            "realtime_start": api["realtime_start"],
            "realtime_end": api["realtime_end"],
            "include_release_dates_with_no_data": str(api["include_release_dates_with_no_data"]).lower(),
            "sort_order": api["sort_order"],
            "limit": api["limit"],
        }
        url = api["base_url"] + "?" + urllib.parse.urlencode(params)
        raw, status = _fetch_json(url)
        (out_dir / f"{print_label}.json").write_bytes(raw)
        provenance.append({
            "print": print_label,
            "release_id": release_id,
            "source_url": _redact(url),
            "http_status": status,
            "retrieved_at_utc": retrieved_at,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        })
        payload = json.loads(raw)
        per_print_dates[print_label] = [row["date"] for row in payload["release_dates"]]

    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2))

    csv_path, exceptions = _normalize(spec, per_print_dates, out_dir, provenance)
    (out_dir / "exceptions.json").write_text(json.dumps(exceptions, indent=2))
    _print_summary(per_print_dates, csv_path, exceptions, out_dir)
    return csv_path


def _normalize(
    spec: dict, per_print_dates: dict[str, list[str]], out_dir: Path, provenance: list[dict]
) -> tuple[Path, dict]:
    """month-1 mapping, earliest-wins collision resolution, gap detection ->
    canonical CSV. Returns (csv_path, exceptions)."""
    rt = spec["release_time"]
    time_et = rt["convention_et"]
    url_by_print = {p["print"]: p["source_url"] for p in provenance}
    overrides = {(o["reference_period"], o["print"]): o["time"] for o in rt.get("overrides") or []}
    provisional = set(spec.get("provisional_reference_prints") or [])

    rows: list[dict] = []
    exceptions = {"collisions": [], "gaps": []}

    for print_label, dates in per_print_dates.items():
        by_ref: dict[dt.date, list[dt.date]] = {}
        for ds in dates:
            d = dt.date.fromisoformat(ds)
            by_ref.setdefault(_reference_month(d), []).append(d)

        for ref, ds in sorted(by_ref.items()):
            ds_sorted = sorted(ds)
            first = ds_sorted[0]
            if len(ds_sorted) > 1:
                exceptions["collisions"].append({
                    "print": print_label,
                    "reference_period": ref.isoformat(),
                    "kept_first_release": first.isoformat(),
                    "also_mapped_here": [x.isoformat() for x in ds_sorted[1:]],
                })
            ref_key = (ref.isoformat(), print_label)
            basis = "override" if ref_key in overrides else "convention_0830ET"
            t = overrides.get(ref_key, time_et)
            ref_basis = (
                "provisional_pending_vintage"
                if print_label in provisional
                else "release_month_minus_1"
            )
            rows.append({
                "print": print_label,
                "reference_period": ref.isoformat(),
                "reference_period_basis": ref_basis,
                "release_date": first.isoformat(),
                "release_datetime_et": f"{first.isoformat()}T{t}",
                "release_time_basis": basis,
                "source_url": url_by_print[print_label],
            })

        # gap detection: consecutive reference months must have no holes
        refs = sorted(by_ref)
        for a, b in zip(refs, refs[1:]):
            expected = dt.date(a.year + (a.month == 12), (a.month % 12) + 1, 1)
            while expected < b:
                exceptions["gaps"].append({"print": print_label, "missing_reference_period": expected.isoformat()})
                expected = dt.date(expected.year + (expected.month == 12), (expected.month % 12) + 1, 1)

    rows.sort(key=lambda r: (r["print"], r["reference_period"]))
    csv_path = out_dir / spec["paths"]["staged_csv"]
    _write_csv(csv_path, spec["output_csv_columns"], rows)
    return csv_path, exceptions


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    import csv
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in columns})


def _print_summary(per_print_dates, csv_path, exceptions, out_dir) -> None:
    print(f"raw + normalized -> {out_dir}")
    for p, ds in per_print_dates.items():
        print(f"  {p:12s} raw_dates={len(ds):4d}  range {min(ds)}..{max(ds)}")
    print(f"  collisions logged: {len(exceptions['collisions'])} | gaps logged: {len(exceptions['gaps'])}")
    print(f"  canonical CSV: {csv_path}")


if __name__ == "__main__":
    fetch(as_of=sys.argv[1] if len(sys.argv) > 1 else None)
