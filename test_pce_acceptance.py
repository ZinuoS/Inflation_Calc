"""Tests for src/nowcast/pce_acceptance.py (Session 3B, Task 2) — gate mechanics."""
from pathlib import Path
import pytest
from nowcast import pce_acceptance as A

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")


def test_rounding_boundary_helpers():
    # 0.1% reporting: 25 bp rounds to 0.3 (nearest 10 = 30->3 tenths? boundaries at 5,15,25,35)
    assert A._reported_tenths(24.0) == 2 and A._reported_tenths(26.0) == 3
    assert A._boundary_dist(25.0) == pytest.approx(0.0)   # exactly on a boundary
    assert A._boundary_dist(20.0) == pytest.approx(5.0)   # mid-band, 5 bp from either side
    assert A._boundary_dist(23.7) == pytest.approx(1.3)


def test_evaluate_and_summary_shape():
    acc = A.evaluate("2024-01-01", "2024-12-01")
    assert len(acc.months) >= 10
    s = A.summarize(acc)
    assert set(["mae_bp", "tier1_pass", "tier2_pass", "tier2_correct_side_pct"]) <= set(s)
    assert isinstance(s["tier1_pass"], bool)


def test_valid_gate_fails_on_true_weights():
    """Valid-gate result (BEA 2.4.5U weights): FAILS Tier 1 (full core, Instrument A). True
    weights removed the WEIGHT bias (degraded was +10.3 bp); the R1 residue respec then added a
    small drift-driven bias (+3.3 bp, H9c over-corrected OOS — documented in R2). Locks in that
    the full-core precision claim fails and runs on true weights."""
    import numpy as np
    acc = A.evaluate("2020-08-01", "2025-12-01")           # instrument A (full core)
    s = A.summarize(acc)
    assert "bea_2.4.5U" in acc.weights_basis               # runs on true BEA weights
    assert s["tier1_pass"] is False and 2.0 < s["mae_bp"] < 12.0
    signed = float(np.mean([x.err_bp for x in acc.months]))
    assert abs(signed) < 6.0                               # far below the +10.3 degraded bias


def test_no_fitted_parameters_marker():
    # the module must stay fit-free (no estimation window); assemble uses frozen proxy weights
    from nowcast import pce_bridge
    _, basis = pce_bridge.pce_weights(allow_approximate=True)
    assert "2022" in basis and "APPROXIMATE" in basis
