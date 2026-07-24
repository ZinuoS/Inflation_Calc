"""Pre-print report generator (Session 6, Task 2/4)."""
import datetime as dt
from pathlib import Path
import pytest
from nowcast import report

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")


def test_info_set_hash_is_deterministic_and_asof_sensitive():
    a = report.info_set_hash("cpi", "2026-06-01", dt.date(2026, 7, 10))
    assert a == report.info_set_hash("cpi", "2026-06-01", dt.date(2026, 7, 10))   # reproducible
    assert a != report.info_set_hash("cpi", "2026-06-01", dt.date(2026, 6, 10))   # different info set


def test_build_call_carries_band_regime_and_freeze_state():
    rec = report.build_call("cpi", "2026-07-01", dt.date(2026, 7, 22))
    for k in ("call_bp", "band_bp", "regime", "frozen", "info_hash", "attribution", "coin_flip"):
        assert k in rec
    assert rec["frozen"] is False           # T-21 is pre-freeze
    assert rec["band_bp"] > 0


def test_page_renders_required_sections():
    rec = report.build_call("pce", "2026-06-01", dt.date(2026, 7, 14))
    page = report.render_page(rec)
    for section in ("pre-print call", "Component attribution", "Running pristine scorecard",
                    "info-set hash", "band"):
        assert section in page
