"""Crosswalk integrity (Task 3): FRED-alias vintages vs BLS-official series.

ALFRED does not archive the raw BLS ids (CUSR0000SAF, ...), so alfred_vintages
uses FRED alias ids (CPIFABSL, ...) and records the crosswalk in
observations.mapping_series_id. This test guards against silent alias drift: for
every (bls_id, alias_id) pair, our latest-vintage alias values must match the
current OFFICIAL series -- fetched from the BLS public API, the authoritative
source for those ids -- within 0.01 index points over the trailing 3 years.

Network test (BLS public API, keyless: one batched request). Skips if the DB is
absent or the BLS API is unreachable; when it runs, a divergence fails loudly and
names the pair.
"""

import datetime as dt
import json
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

import pytest

DB = Path(__file__).parent.parent / "data" / "db" / "nowcast.sqlite"
TOLERANCE = 0.01
BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="nowcast.sqlite not built")


def _bls_fetch(series_ids: list[str], start_year: int, end_year: int) -> dict[str, dict[str, float]]:
    body = json.dumps(
        {"seriesid": series_ids, "startyear": str(start_year), "endyear": str(end_year)}
    ).encode()
    req = urllib.request.Request(
        BLS_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "inflation-nowcast-research/0.1"},
    )
    try:
        payload = json.load(urllib.request.urlopen(req, timeout=45))
    except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover - network
        pytest.skip(f"BLS API unreachable: {exc}")
    if payload.get("status") != "REQUEST_SUCCEEDED":
        pytest.skip(f"BLS API status {payload.get('status')}: {payload.get('message')}")

    out: dict[str, dict[str, float]] = {}
    for series in payload["Results"]["series"]:
        month = {}
        for point in series["data"]:
            if not point["period"].startswith("M"):
                continue
            try:
                month[f"{point['year']}-{point['period'][1:]}-01"] = float(point["value"])
            except ValueError:
                continue  # BLS placeholder for a missing value
        out[series["seriesID"]] = month
    return out


def test_alias_matches_official_bls_series():
    conn = sqlite3.connect(DB)
    pairs = conn.execute(
        "SELECT DISTINCT mapping_series_id, series_id FROM observations "
        "WHERE mapping_series_id <> series_id"
    ).fetchall()
    assert pairs, "no crosswalk pairs found"

    end_year = dt.date.today().year
    start_year = end_year - 3
    official = _bls_fetch([bls for bls, _ in pairs], start_year, end_year)

    cutoff = (dt.date.today().replace(day=1) - dt.timedelta(days=365 * 3)).isoformat()
    failures = []
    checked = 0
    for bls_id, alias_id in pairs:
        bls_series = official.get(bls_id)
        if not bls_series:
            # some ids (e.g. a PPI WPS series) may not return from this endpoint;
            # a missing official series can't confirm OR deny drift -> don't fail on it
            continue
        db_series = dict(
            conn.execute(
                "SELECT reference_period, latest_value FROM latest_value "
                "WHERE series_id = ? AND reference_period >= ?",
                (alias_id, cutoff),
            )
        )
        common = set(bls_series) & set(db_series)
        if not common:
            continue
        max_diff = max(abs(bls_series[m] - db_series[m]) for m in common)
        checked += 1
        if max_diff > TOLERANCE:
            worst = max(common, key=lambda m: abs(bls_series[m] - db_series[m]))
            failures.append(
                f"{alias_id} vs official {bls_id}: max|diff|={max_diff:.4f} at {worst} "
                f"(bls={bls_series[worst]}, ours={db_series[worst]})"
            )
    conn.close()

    assert checked > 0, "no crosswalk pairs could be compared against BLS"
    assert not failures, "crosswalk drift detected:\n  " + "\n  ".join(failures)
