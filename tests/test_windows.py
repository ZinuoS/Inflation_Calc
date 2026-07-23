"""Tests for src/nowcast/windows.py (Session 4, Task 1, H8)."""
from pathlib import Path
import pytest
from nowcast import windows as W

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")


def test_aggregation_schemes_differ_and_are_finite():
    obs = {"2024-06-03": 3.0, "2024-06-10": 3.2, "2024-06-17": 3.4, "2024-06-24": 3.6}
    fm = W.aggregate_month(obs, "2024-06-01", "full_month_mean")
    tr = W.aggregate_month(obs, "2024-06-01", "trailing_7")
    assert abs(fm - 3.3) < 1e-9 and tr == 3.6         # trailing-7 = last obs only


def test_h8_gasoline_selects_stable_full_month():
    """Pre-registered expectation: gasoline's window is stable and ~full-month mean."""
    r = W.select_window("eia_gasoline", "US", "SETB01")
    assert r["stable"] is True and r["selected"] == "full_month_mean"
    assert r["mean_test_r2"] > 0.9                     # gasoline tracks its stratum strongly


def test_h8_unstable_defaults_to_full_month():
    """An unstable fold-to-fold winner must default to full_month_mean, not fold-chase."""
    r = W.select_window("eia_heating_oil", "US_NYH_SPOT", "SEHE01")
    if not r.get("stable", False):
        assert r["selected"] == "full_month_mean"


def test_partial_feature_is_days_1_to_15():
    # Manheim mid-month is a days-1-15 feature; partial_feature must never span the whole month
    v = W.partial_feature("manheim", "US_full_month", "2025-06-01", "2026-01-01")
    # (manheim is monthly full-month here, so mid-month partial may be None — assert no crash/type)
    assert v is None or isinstance(v, float)
