"""Edge fetcher for bls_cpi_series (Session 2B, Group C).

Downloads BLS CPI bulk flat files, filters to US-city-average SA+NSA series for every
mapping.yaml item code, emits the uniform official_current staged CSV. Deterministic
parse per spec.yaml. official_current = methodology replication only (3A/3B), never a
backtest target.
"""
from __future__ import annotations
import datetime as dt, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _ingest  # noqa: E402
PIPE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]


def mapping_item_codes() -> set[str]:
    m = yaml.safe_load((REPO / "mapping" / "mapping.yaml").read_text())
    return {d["item_code"] for d in m["cpi"]["items"] if d.get("item_code")}


def parse_flat(text: str, codes: set[str], spec: dict, observed_date: str) -> list[dict]:
    """BLS flat TSV -> uniform official_current rows for mapping SA/NSA series. Pure."""
    p = spec["parse"]
    sa, nsa = p["series_prefix_sa"], p["series_prefix_nsa"]
    wanted = {sa + c: (c, "SA") for c in codes} | {nsa + c: (c, "NSA") for c in codes}
    rows = []
    for line in text.splitlines():
        if not line or line.startswith("series_id"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        sid = parts[0].strip()
        if sid not in wanted:
            continue
        period = parts[2].strip()
        if not period.startswith("M") or period == "M13":
            continue
        value = parts[3].strip()
        if value in ("", "-"):
            continue
        item_code, seasonal = wanted[sid]
        rows.append({
            "source": spec["source"], "series_id": sid, "item_code": item_code,
            "seasonal": seasonal, "frequency": "monthly",
            "period": f"{parts[1].strip()}-{period[1:]}-01", "value": value,
        })
    return rows


def ensure_indexed_official_table(db_path) -> None:
    """# SHIM: pending naru#7 -- naru's per-row supersede UPDATE has no key index, so
    a from-scratch bulk load of official_current (~268k rows) is O(n^2) and never
    finishes. Pre-create the naru final table AND its (series_id, period) key index
    here, so the subsequent naru run loads into an already-indexed table in seconds.
    Idempotent (CREATE ... IF NOT EXISTS); makes a rebuild deterministic with no
    runbook step."""
    from naru import store
    from naru.artifact import load_artifact

    from nowcast import db

    art = load_artifact(REPO / "pipelines" / "official_loader" / "v1")
    with db.connect(db_path) as conn:
        store.create_final_table(conn, art.manifest.target_table, art.target_row)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_official_key ON official_current(series_id, period)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_official_active "
            "ON official_current(series_id, _superseded_by_run_id)"
        )
        conn.commit()


def fetch(as_of: str | None = None) -> Path:
    spec = yaml.safe_load((PIPE / "spec.yaml").read_text())
    as_of = as_of or dt.date.today().isoformat()
    out = _ingest.raw_dir(spec["source"], as_of)
    codes = mapping_item_codes()

    all_rows, prov = [], []
    for fname in spec["files"]:
        url = spec["base_url"] + fname
        raw, status = _ingest.fetch(url)
        (out / fname).write_bytes(raw)
        prov.append({"label": fname, "source_url": url, "http_status": status,
                     "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "sha256": _ingest.sha256(raw), "bytes": len(raw)})
        all_rows += parse_flat(raw.decode("utf-8", "replace"), codes, spec, as_of)
    prov_path = _ingest.write_provenance(out, prov)

    # dedup (a series can appear in >1 file, e.g. AllItems + a group file)
    seen, deduped = set(), []
    for r in all_rows:
        k = (r["series_id"], r["period"])
        if k not in seen:
            seen.add(k); deduped.append(r)
    staged = out / "staged.csv"
    import csv as _csv
    with open(staged, "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=["source","series_id","item_code","seasonal","frequency","period","value"])
        w.writeheader()
        for r in deduped:
            w.writerow(r)
    n_series = len({r["series_id"] for r in deduped})
    print(f"bls_cpi: {len(deduped)} rows, {n_series} series (SA+NSA)")
    return staged, prov_path, as_of


if __name__ == "__main__":
    staged, prov, as_of = fetch(sys.argv[1] if len(sys.argv) > 1 else None)
    from naru.runtime import run as naru_run
    from nowcast.provenance import record_fetch_provenance
    ensure_indexed_official_table(REPO / "data/db/nowcast.sqlite")  # SHIM naru#7, before bulk load
    res = naru_run(artifact_path=REPO/"pipelines/official_loader/v1", input_path=staged,
                   db_path=REPO/"data/db/nowcast.sqlite", raw_dir=REPO/"data/db/naru_raw",
                   as_of=dt.date.fromisoformat(as_of))
    record_fetch_provenance(REPO/"data/db/nowcast.sqlite","bls_cpi_series",prov,staged,naru_run_id=res.run_id)
    print(f"bls_cpi: loaded {len(res.row_ids)} rows into official_current")
