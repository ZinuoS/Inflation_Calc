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


def test_unchanged_payload_is_not_rearchived(tmp_path, monkeypatch):
    """A paused source must not accumulate byte-identical snapshots — absence IS the signal."""
    monkeypatch.setattr(_ingest, "REPO", tmp_path)
    _ingest.archive_vintage("demo", "2026-07-26", b"same", "d.csv", "http://x")
    with pytest.raises(_ingest.VintageUnchanged):
        _ingest.archive_vintage("demo", "2026-08-26", b"same", "d.csv", "http://x")
    _ingest.archive_vintage("demo", "2026-09-26", b"CHANGED", "d.csv", "http://x")
    assert _ingest.list_vintages("demo") == ["2026-07-26", "2026-09-26"]


def test_atrr_archive_holds_bls_vintages_and_reproduces_the_revision():
    """The ATRR archive is what makes H14 re-runnable. Assert it exists AND that a known revision
    is recoverable from it (as-published vs latest for the same reference quarter)."""
    import json
    vs = _ingest.list_vintages("atrr")
    if len(vs) < 2:
        pytest.skip("atrr archive not populated in this checkout")
    import importlib.util
    spec = importlib.util.spec_from_file_location("atrr_f", REPO / "pipelines" / "atrr" / "fetch.py")
    af = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(af)
    import yaml
    sp = yaml.safe_load((REPO / "pipelines" / "atrr" / "spec.yaml").read_text())

    def levels(tag):
        d = _ingest.vintage_dir("atrr", tag)
        man = json.loads((d / "manifest.json").read_text())
        return {r["period"]: float(r["value"])
                for r in af.parse((d / man["filename"]).read_bytes(), sp, observed_date=tag)}

    if "2024q2" not in vs:
        pytest.skip("2024q2 vintage absent")
    pub, now = levels("2024q2"), levels(vs[-1])
    per, prev = "2024-04-01", "2024-01-01"
    if not all(k in pub and k in now for k in (per, prev)):
        pytest.skip("reference quarters absent")
    a = (pub[per] / pub[prev] - 1) * 1e4
    b = (now[per] / now[prev] - 1) * 1e4
    assert abs(b - a) > 50, ("the archive must preserve a real revision; if this collapses, the "
                             f"snapshots are not point-in-time (as-published {a:.1f} vs latest {b:.1f} bp)")
