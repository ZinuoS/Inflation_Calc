"""Tests for src/nowcast/intramonth.py (Session 4, Task 5)."""
import datetime as dt
from pathlib import Path
import pytest
from nowcast import intramonth as IM

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")


def test_freeze_is_enforced_after_t4():
    """An as-of date past T-4 must be clamped to the T-4 date (freeze enforced, not documented)."""
    import sqlite3
    c = sqlite3.connect(str(DB)); rel = IM._release_date(c, "2026-05-01"); c.close()
    late = IM.nowcast_as_of("2026-05-01", rel - dt.timedelta(days=1), "headline")   # T-1, past freeze
    assert late["frozen"] is True
    assert late["effective_asof"] == (rel - dt.timedelta(days=IM.FREEZE_LEAD_DAYS)).isoformat()
    early = IM.nowcast_as_of("2026-05-01", rel - dt.timedelta(days=20), "headline")  # T-20, not frozen
    assert early["frozen"] is False


def test_tminus_path_shape_and_monotone_days():
    path = IM.tminus_path("2026-05-01", "headline", tmax=20, tmin=3)
    assert len(path) == 18 and path[0]["days_to_release"] == 20 and path[-1]["days_to_release"] == 3
    assert all(p["forecast_mom"] is not None for p in path)
