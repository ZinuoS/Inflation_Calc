"""Fetch-provenance recording — SHIM: pending naru#2.

naru's raw_files registry stores (sha256, original_name, run_id) but not the
(url, retrieved_at) that CLAUDE.md rule 4 requires. Until naru records fetch
provenance natively (naru#2), the edge fetcher writes a provenance.json sidecar
and this module loads it into a repo-side `meta_fetch_provenance` table in the
same nowcast.sqlite, joinable to naru's lineage by the ingested file's sha256.

Chain of custody, end to end:
  release_calendar.row  --meta_lineage.file_sha256-->  the normalized.csv naru
  ingested  --meta_fetch_provenance.artifact_sha256-->  the upstream FRED URL +
  retrieval time + upstream JSON sha256 that produced it.

This is deterministic and offline: it only reads a JSON the fetcher already wrote.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

_DDL = """
CREATE TABLE IF NOT EXISTS meta_fetch_provenance (
    pipeline TEXT NOT NULL,
    label TEXT NOT NULL,              -- which upstream object (e.g. print: CPI)
    source_url TEXT NOT NULL,         -- api_key REDACTED
    retrieved_at_utc TEXT NOT NULL,
    http_status INTEGER,
    upstream_sha256 TEXT NOT NULL,    -- hash of the raw upstream bytes (the JSON)
    bytes INTEGER,
    artifact_sha256 TEXT NOT NULL,    -- hash of the file naru actually ingested (the CSV)
    naru_run_id INTEGER,
    PRIMARY KEY (pipeline, label, upstream_sha256, artifact_sha256)
);
"""


def record_fetch_provenance(
    db_path: Path,
    pipeline: str,
    provenance_json: Path,
    ingested_file: Path,
    naru_run_id: int | None = None,
) -> int:
    """Load a fetcher's provenance.json into meta_fetch_provenance, tying each
    upstream pull to the sha256 of the file naru ingested. Returns rows written.
    """
    records = json.loads(Path(provenance_json).read_text())
    artifact_sha = hashlib.sha256(Path(ingested_file).read_bytes()).hexdigest()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_DDL)
        rows = [
            (
                pipeline,
                r.get("print", r.get("label", "")),
                r["source_url"],
                r["retrieved_at_utc"],
                r.get("http_status"),
                r["sha256"],
                r.get("bytes"),
                artifact_sha,
                naru_run_id,
            )
            for r in records
        ]
        conn.executemany(
            "INSERT OR REPLACE INTO meta_fetch_provenance "
            "(pipeline, label, source_url, retrieved_at_utc, http_status, "
            " upstream_sha256, bytes, artifact_sha256, naru_run_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()
