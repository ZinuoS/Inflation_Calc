"""Edge fetcher for nadac (Session 2B, Task 3). CMS NADAC per-NDC -> monthly index.

Index is a PLACEHOLDER matched-model geomean-of-relatives (marked for 3A upgrade)."""
from __future__ import annotations
import csv, datetime as dt, io, math, sys
from collections import defaultdict
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402
PIPE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]


def monthly_ndc_means(csv_bytes: bytes, cols: dict, acc: dict, date_format: str) -> None:
    """Accumulate sum/count of NADAC per unit per (ndc, month) across files. Pure-ish.

    Header drift across NADAC vintages is deterministic: older files use underscores
    (NADAC_Per_Unit, Effective_Date), newer files use spaces. We normalize
    underscore->space so one spec column mapping matches both -- no per-file guessing.
    """
    r = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8", "replace")))
    for rec in r:
        rec = {k.replace("_", " "): v for k, v in rec.items()}
        try:
            price = float(rec[cols["price"]])
            d = dt.datetime.strptime(rec[cols["date"]], date_format).date()
        except (ValueError, KeyError):
            continue
        key = (rec[cols["ndc"]], d.replace(day=1).isoformat())
        s = acc.setdefault(key, [0.0, 0])
        s[0] += price; s[1] += 1


def build_index(acc: dict, spec: dict) -> tuple[list[dict], int]:
    """Matched-model geomean-of-relatives chained index. Returns (rows, skipped_months)."""
    by_month: dict[str, dict[str, float]] = defaultdict(dict)
    for (ndc, month), (tot, n) in acc.items():
        by_month[month][ndc] = tot / n
    months = sorted(by_month)
    br = spec["basket_rule"]
    idx = br["base"]
    rows, skipped = [], 0
    prev_month = None
    for m in months:
        if prev_month is None:
            rows.append((m, idx)); prev_month = m; continue
        common = set(by_month[m]) & set(by_month[prev_month])
        if len(common) < br["min_matched_ndcs"]:
            skipped += 1; prev_month = m; continue
        rel = math.exp(sum(math.log(by_month[m][c] / by_month[prev_month][c]) for c in common) / len(common))
        idx *= rel
        rows.append((m, idx)); prev_month = m
    staged = [{"source": spec["source"], "series_key": spec["series_key"], "frequency": "monthly",
               "period": m, "value": f"{v:.6f}", "vintage_status": spec["vintage_status"],
               "observed_date": m} for m, v in rows]
    return staged, skipped


def fetch(as_of: str | None = None):
    spec = yaml.safe_load((PIPE / "spec.yaml").read_text())
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)
    acc, prov = {}, []
    for year in spec["years"]:
        url = spec["year_urls"][year]  # deterministic, catalog-enumerated (no guessing)
        try:
            raw, status = _ingest.fetch(url, timeout=300)
        except Exception as e:
            print(f"nadac: {year} fetch failed ({e}); skipping"); continue
        (out / f"nadac_{year}.csv").write_bytes(raw)
        prov.append({"label": f"nadac_{year}", "source_url": url, "http_status": status,
                     "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "sha256": _ingest.sha256(raw), "bytes": len(raw)})
        monthly_ndc_means(raw, spec["columns"], acc, spec["date_format"])
        print(f"nadac: {year} parsed, cumulative (ndc,month) keys={len(acc)}")
    prov_path = _ingest.write_provenance(out, prov)
    staged_rows, skipped = build_index(acc, spec)
    staged = out / "staged.csv"
    _ingest.write_staged_csv(staged, staged_rows)
    print(f"nadac: {len(staged_rows)} monthly index points, {skipped} months skipped (thin basket)")
    n = _ingest.load(spec["source"], staged, prov_path, as_of)
    print(f"nadac: loaded {n} rows")
    return staged


if __name__ == "__main__":
    fetch(sys.argv[1] if len(sys.argv) > 1 else None)
