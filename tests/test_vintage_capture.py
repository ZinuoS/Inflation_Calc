"""Task 3 — forward vintage capture. The archive's only value is that it is IMMUTABLE:
a snapshot that can be silently replaced is not point-in-time evidence.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "pipelines"))
import _ingest  # noqa: E402

REVISED_SOURCES = ("zori", "atlanta_fed_wage", "indeed_wage")


def test_archive_refuses_to_overwrite_an_existing_vintage(tmp_path, monkeypatch):
    monkeypatch.setattr(_ingest, "REPO", tmp_path)
    d = _ingest.archive_vintage("demo", "2026-07-26", b"v1", "d.csv", "http://x", rows=3)
    assert (d / "d.csv").read_bytes() == b"v1"
    with pytest.raises(_ingest.VintageExists):
        _ingest.archive_vintage("demo", "2026-07-26", b"v2-DIFFERENT", "d.csv", "http://x")
    assert (d / "d.csv").read_bytes() == b"v1", "existing snapshot must survive untouched"


def test_distinct_dates_coexist_and_are_listed(tmp_path, monkeypatch):
    monkeypatch.setattr(_ingest, "REPO", tmp_path)
    _ingest.archive_vintage("demo", "2026-07-26", b"a", "d.csv", "http://x")
    _ingest.archive_vintage("demo", "2026-10-26", b"b", "d.csv", "http://x")
    assert _ingest.list_vintages("demo") == ["2026-07-26", "2026-10-26"]


def test_manifest_records_what_a_rerun_would_need(tmp_path, monkeypatch):
    monkeypatch.setattr(_ingest, "REPO", tmp_path)
    d = _ingest.archive_vintage("demo", "2026-07-26", b"abc", "d.csv", "http://x",
                                rows=5, period_min="2020-01-01", period_max="2026-06-01")
    man = json.loads((d / "manifest.json").read_text())
    for k in ("source", "vintage_date", "sha256", "bytes", "rows", "period_min", "period_max",
              "source_url", "retrieved_at_utc", "vintage_status"):
        assert man[k] not in (None, ""), f"manifest missing {k}"
    assert man["sha256"] == _ingest.sha256(b"abc")
    assert man["vintage_status"] == "revised_latest_only"


def test_every_revised_source_pipeline_wires_capture():
    """A revised_latest_only source whose fetch() does not archive is a silent data-loss bug."""
    for src in REVISED_SOURCES:
        f = REPO / "pipelines" / src / "fetch.py"
        assert f.exists(), f"{src} pipeline missing"
        assert "archive_vintage" in f.read_text(), f"{src}/fetch.py does not capture vintages"


def test_committed_zori_vintage_is_intact():
    """The live capture proved out on a real pull; its manifest must stay self-consistent."""
    vs = _ingest.list_vintages("zori")
    if not vs:
        pytest.skip("no zori vintage captured in this checkout")
    d = _ingest.vintage_dir("zori", vs[-1])
    man = json.loads((d / "manifest.json").read_text())
    payload = (d / man["filename"]).read_bytes()
    assert _ingest.sha256(payload) == man["sha256"], "snapshot mutated since capture"
    assert man["bytes"] == len(payload)
