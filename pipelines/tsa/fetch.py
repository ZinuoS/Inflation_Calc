"""Edge fetcher for tsa (Session 2B-final, B5) — TSA daily throughput -> monthly mean.
MONITOR (demand context for airfares), not a price proxy."""
from __future__ import annotations
import datetime as dt, re, sys
from collections import defaultdict
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402
PIPE = Path(__file__).resolve().parent


def parse(html: str, spec: dict, observed_date: str) -> list[dict]:
    """TSA HTML table -> monthly-mean staged rows (complete months only). Pure/testable."""
    p = spec["parse"]
    daily: dict[str, list[float]] = defaultdict(list)
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 2:
            continue
        try:
            d = dt.datetime.strptime(cells[0], p["date_format"]).date()
            n = float(cells[1].replace(",", ""))
        except ValueError:
            continue
        daily[d.replace(day=1).isoformat()].append(n)
    # complete months only: a month is complete if its data covers to month-end
    rows = []
    today = dt.date.today()
    for month, vals in sorted(daily.items()):
        md = dt.date.fromisoformat(month)
        # drop the current (partial) month
        if p.get("complete_months_only") and md.year == today.year and md.month == today.month:
            continue
        rows.append({"source": spec["source"], "series_key": spec["series_key"],
                     "frequency": "monthly", "period": month, "value": f"{sum(vals)/len(vals):.1f}",
                     "vintage_status": spec["vintage_status"], "observed_date": observed_date})
    return rows


def fetch(as_of: str | None = None):
    spec = yaml.safe_load((PIPE / "spec.yaml").read_text())
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)
    raw, status = _ingest.fetch(spec["url"])
    (out / "passenger-volumes.html").write_bytes(raw)
    prov = [{"label": "tsa_throughput", "source_url": spec["url"], "http_status": status,
             "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
             "sha256": _ingest.sha256(raw), "bytes": len(raw)}]
    prov_path = _ingest.write_provenance(out, prov)
    rows = parse(raw.decode("utf-8", "replace"), spec, as_of)
    staged = out / "staged.csv"
    _ingest.write_staged_csv(staged, rows)
    print(f"tsa: {len(rows)} complete-month rows {rows[0]['period']}..{rows[-1]['period']}" if rows else "tsa: 0 rows")
    n = _ingest.load(spec["source"], staged, prov_path, as_of)
    print(f"tsa: loaded {n} rows")
    return staged


if __name__ == "__main__":
    fetch(sys.argv[1] if len(sys.argv) > 1 else None)
