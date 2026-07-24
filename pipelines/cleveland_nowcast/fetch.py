"""Edge fetcher for cleveland_nowcast (Session 8) — Federal Reserve Bank of Cleveland
inflation nowcast, the vintage-safe pre-release BENCHMARK.

The public webchart JSON is 157 MONTHLY frames (2013-07 .. current). Each frame holds the DAILY
nowcast path for that stretch, with vertical rules labelled `CPI {mon}` / `PCE {mon}` marking each
release. The nowcast value immediately BEFORE a `{fam} {mon}` vline is the model's FINAL pre-release
nowcast for that reference month — exactly the point-in-time value a forecaster could have read a
day or two before the print. `observed_asof` = that last business-day label; strictly < release.

Benchmark, NOT a proxy feature and NOT a backtest target. Output is a derived eval artifact
(`data/benchmarks/cleveland_nowcast.csv`), kept physically OUTSIDE proxy_observations so it can
never leak into the feature firewall. Values are % MoM, seasonally adjusted (the market variable).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402

PIPE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
URL = "https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json"
OUT_CSV = REPO / "data" / "benchmarks" / "cleveland_nowcast.csv"

MON = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
SERIES = {"CPI Inflation": ("cpi_headline", "CPI"),
          "Core CPI Inflation": ("cpi_core", "CPI"),
          "PCE Inflation": ("pce_headline", "PCE"),
          "Core PCE Inflation": ("pce_core", "PCE")}
COLS = ["source", "series_key", "reference_month", "value_pct_mom_sa", "observed_asof",
        "vintage_status"]


def parse(payload: bytes) -> list[dict]:
    """Cleveland webchart JSON -> one row per (series, reference_month): the final pre-release
    nowcast. Pure/testable. Keeps the latest-asof value when a month appears in >1 frame."""
    frames = json.loads(payload)
    best: dict[tuple, tuple] = {}          # (series_key, ref) -> (asof, value)
    for fr in frames:
        fy, _fm = map(int, fr["chart"]["subcaption"].split("-"))
        cats = fr["categories"][0]["category"]
        # attach a real calendar date to each MM/DD label, rolling the year forward at wrap
        caldate, cur_y, prev_mm = [], fy, None
        for c in cats:
            m = re.match(r"(\d{2})/(\d{2})$", c["label"])
            if m:
                mm, dd = int(m.group(1)), int(m.group(2))
                if prev_mm is not None and mm < prev_mm:
                    cur_y += 1
                prev_mm = mm
                caldate.append(dt.date(cur_y, mm, dd))
            else:
                caldate.append(None)
        data = {s["seriesname"]: s["data"] for s in fr["dataset"]}
        for j, c in enumerate(cats):
            vm = re.match(r"(CPI|PCE) (\w{3})$", c["label"]) if c.get("vline") else None
            if not vm:
                continue
            fam, mon = vm.group(1), MON[vm.group(2)]
            yctx = next((caldate[k].year for k in range(j - 1, -1, -1) if caldate[k]), fy)
            ref = dt.date(yctx, mon, 1).isoformat()
            for sname, (skey, sfam) in SERIES.items():
                if sfam != fam or sname not in data:
                    continue
                for k in range(j - 1, -1, -1):
                    v = data[sname][k].get("value") if k < len(data[sname]) else None
                    if v not in (None, ""):
                        asof = caldate[k]
                        # Sanity guard against cross-year frame mis-assignment: a release lands
                        # ~11-60 days after the reference month; anything outside that is a parse
                        # artifact (e.g. a Dec ref picking up a Feb as-of on a wrapped frame).
                        rd = dt.date.fromisoformat(ref)
                        if asof and (dt.timedelta(days=10) <= (asof - rd) <= dt.timedelta(days=80)):
                            key = (skey, ref)
                            if key not in best or (best[key][0] and asof > best[key][0]):
                                best[key] = (asof, float(v))
                        break
    rows = []
    for (skey, ref), (asof, val) in sorted(best.items()):
        if asof is None:
            continue
        rows.append({"source": "cleveland_nowcast", "series_key": skey, "reference_month": ref,
                     "value_pct_mom_sa": f"{val:.6f}", "observed_asof": asof.isoformat(),
                     "vintage_status": "point_in_time"})
    return rows


def write_csv(rows: list[dict], path: Path = OUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def fetch(as_of: str | None = None):
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir("cleveland_nowcast", as_of)
    raw, status = _ingest.fetch(URL)
    (out / "nowcast_month.json").write_bytes(raw)
    prov = [{"label": "cleveland_inflation_nowcast", "source_url": URL, "http_status": status,
             "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
             "sha256": _ingest.sha256(raw), "bytes": len(raw)}]
    _ingest.write_provenance(out, prov)
    rows = parse(raw)
    write_csv(rows)
    print(f"cleveland_nowcast: {len(rows)} (series,month) rows -> {OUT_CSV.relative_to(REPO)}")
    return rows


if __name__ == "__main__":
    fetch()
