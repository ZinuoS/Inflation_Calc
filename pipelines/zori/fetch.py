"""Edge fetcher for zori (Session 2B, Group A). The only network step.

Downloads the ZORI metro+US wide CSV, keeps the immutable raw pull, extracts the
US national row, and emits the uniform proxy staged CSV (one monthly row) for the
shared proxy_loader artifact. Deterministic parse per spec.yaml.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402

PIPE = Path(__file__).resolve().parent


def parse(raw_bytes: bytes, spec: dict, observed_date: str) -> list[dict]:
    """ZORI wide CSV -> uniform staged rows for the US national row. Pure/testable."""
    import csv
    import io

    p = spec["parse"]
    reader = csv.reader(io.StringIO(raw_bytes.decode("utf-8")))
    header = next(reader)
    date_cols = header[p["first_value_col_index"]:]
    name_idx = header.index(p["region_name_col"])
    rows: list[dict] = []
    for record in reader:
        if record[name_idx] != p["select_region"]:
            continue
        for i, month_end in enumerate(date_cols):
            raw_val = record[p["first_value_col_index"] + i]
            if raw_val == "":
                continue
            period = dt.date.fromisoformat(month_end).replace(day=1).isoformat()
            rows.append({
                "source": spec["source"],
                "series_key": spec["series_key"],
                "frequency": p["frequency"],
                "period": period,
                "value": raw_val,
                "vintage_status": spec["vintage_status"],
                "observed_date": observed_date,
            })
        break
    return rows


def fetch(as_of: str | None = None) -> Path:
    spec = yaml.safe_load((PIPE / "spec.yaml").read_text())
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)

    raw, status = _ingest.fetch(spec["url"])
    (out / "Metro_zori_sa_month.csv").write_bytes(raw)
    prov = [{
        "label": "zori_metro_sa",
        "source_url": spec["url"],
        "http_status": status,
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sha256": _ingest.sha256(raw),
        "bytes": len(raw),
    }]
    prov_path = _ingest.write_provenance(out, prov)

    rows = parse(raw, spec, observed_date=as_of)
    staged = out / "staged.csv"
    _ingest.write_staged_csv(staged, rows)
    print(f"zori: {len(rows)} monthly rows  {rows[0]['period']}..{rows[-1]['period']}")
    # Task 3 — forward vintage capture: this source restates its own history and publishes
    # no vintage archive, so every pull archives an immutable full-history snapshot.
    try:
        v = _ingest.archive_vintage(spec["source"], as_of, raw, "Metro_zori_sa_month.csv",
                                    spec["url"], rows=len(rows),
                                    period_min=rows[0]["period"], period_max=rows[-1]["period"])
        print(f"vintage captured: {v.name} ({len(rows)} rows)")
    except _ingest.VintageExists as e:
        print(f"vintage already captured today; not overwritten ({e})")

    n = _ingest.load(spec["source"], staged, prov_path, as_of)
    print(f"zori: loaded {n} rows into proxy_observations")
    return staged


if __name__ == "__main__":
    fetch(sys.argv[1] if len(sys.argv) > 1 else None)
