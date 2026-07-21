"""Tests for src/nowcast/pce_bridge.py (Session 3B, Task 1). Imputed components unit-tested in
isolation with their rationale; assembly mechanics and the honest data-readiness flags."""
import datetime as dt
from pathlib import Path

import pytest

from nowcast import pce_bridge as B

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")


def test_weights_unavailable_without_bea_or_approx():
    """No PCE weights without bea_pce_detail unless approximation is explicitly allowed —
    the gate must opt in to proxy weights, never get them silently."""
    with pytest.raises(B.WeightsUnavailable):
        B.pce_weights(allow_approximate=False)
    w, basis = B.pce_weights(allow_approximate=True)
    assert "APPROXIMATE" in basis and len(w) > 20


def test_imputed_group_housing_tracks_rent():
    """group_housing (dorms/group homes) has no market price; BEA input-cost tracks shelter,
    so we proxy it by tenant rent (SEHA) — must return a rent-like relative, not frozen."""
    from nowcast import db
    from nowcast.timebase import open_timebase
    with db.connect(str(DB)) as conn, open_timebase(str(DB)) as tb:
        vint = B._vintaged_series(conn)
        rel, vintflag, method = B._imputed_relative("group_housing", "2024-09-01", tb, conn, vint, dt.datetime(2026, 7, 1), {})
    assert rel is not None and 0.98 < rel < 1.02 and "SEHA" in method


def test_imputed_no_analogue_components_are_frozen_and_flagged():
    """health_insurance_margin / life_insurance / npish have no CPI analogue -> frozen 1.0
    (a KNOWN unattributable gap, not a silent guess); financial-services needs the S&P path."""
    from nowcast import db
    with db.connect(str(DB)) as conn:
        for name in ("health_insurance_margin", "life_insurance", "npish_final_consumption"):
            rel, vint, method = B._imputed_relative(name, "2024-09-01", None, conn, set(), None, {})
            assert rel == 1.0 and vint == "imputed" and "frozen" in method
        # financial services now follows the S&P equity path (data ingested)
        rel, vint, method = B._imputed_relative("financial_services_without_payment", "2024-09-01", None, conn, set(), None, {})
        assert rel is not None and method == "sp500_path" and vint == "equity_path"


def test_portfolio_ppi_discontinued_boundary():
    """Portfolio-management PPI is discontinued 2022-12; post-boundary needs the S&P path
    (absent) so it is flagged absent, not silently carried on a dead series."""
    from nowcast import db
    from nowcast.timebase import open_timebase
    with db.connect(str(DB)) as conn, open_timebase(str(DB)) as tb:
        rel, _, m_post = B._ppi_relative(tb, conn, "PCU523920523920", "2024-09-01", dt.datetime(2100, 1, 1))
        assert m_post == "sp500_path" and rel is not None  # post-2022 uses the equity path


def test_assemble_runs_and_reports_leakage_and_coverage():
    """The bridge assembles a number under approximate weights AND honestly reports how much
    core weight was priced and how much was read latest-vintage (leakage-exposed)."""
    res = B.assemble_core_pce_mom("2024-09-01", dt.datetime(2024, 11, 1), allow_approximate_weights=True)
    assert res.core_pce_mom is not None
    assert 0.0 < res.covered_weight <= 1.0
    assert 0.0 <= res.latest_vintage_weight <= 1.0
    # rent/OER carry true first-release; most others are latest-vintage
    firs = [c for c in res.components if c.vintage == "first_release"]
    assert any(c.component == "housing_tenant_rent" for c in firs)


def test_inventory_covers_every_core_component():
    core = [r for r in B.component_inventory() if r["in_core"]]
    assert len(core) == 34
    assert {r["status"] for r in core} <= {"implemented", "approximated", "absent"}
