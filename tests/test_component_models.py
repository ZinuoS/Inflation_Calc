"""Tests for src/nowcast/component_models.py (Session 4, Task 2)."""
import datetime as dt
from pathlib import Path
import pytest
from nowcast import component_models as CM

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")
FT = dt.date(2025, 7, 15)   # ~ a 2025-06 CPI release day


def test_gasoline_is_imposed_pass_through_of_the_proxy():
    cfg = CM._cfg()
    pm = CM._proxy_month_mom("eia_gasoline", "US", "2025-06-01", "full_month_mean", FT, str(DB))
    f = CM.forecast_component("SETB01", "2025-06-01", FT, cfg)
    assert pm is not None and f == pytest.approx(0.965 * pm, abs=1e-9)   # beta imposed, no fit


def test_unconfigured_stratum_uses_seasonal_baseline():
    f = CM.forecast_component("SEHF01", "2025-06-01", FT)   # electricity, no proxy config
    assert f is not None and abs(f) < 0.2                    # a sane monthly rate


def test_aggregate_nowcast_uses_the_stratum_proxies():
    r = CM.forecast_aggregate_nsa("2025-06-01", FT, "headline")
    assert r["forecast_mom"] is not None
    assert r["n_proxy_driven"] >= 1 and r["proxy_weight_share"] > 0   # gasoline/used-cars applied
    assert r["degraded_feature_set"] == "no_keepa_goods_panel"        # standing annotation
