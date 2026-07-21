"""Tests for src/nowcast/aggregate.py — CPI aggregation replication (Session 3A, Task 5).
Real-DB (skips if nowcast.sqlite absent)."""
from pathlib import Path

import pytest

from nowcast import aggregate as A

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")


def test_headline_partition_is_the_eight_majors():
    """No exclusions -> the coarsest complete partition of All items is exactly the 8 major
    groups (each already carries BLS's exact sub-aggregation), not a finer set."""
    part = set(A.complete_published_partition("SA0"))
    assert part == {"SAF", "SAH", "SAA", "SAT", "SAM", "SAR", "SAE", "SAG"}


def test_core_partition_excludes_food_and_energy_and_weights_to_core_share():
    part = A.complete_published_partition("SA0", (A.FOOD_SUBTREE, *A.ENERGY_SUBTREES))
    from nowcast import weights
    RI = weights.weights_as_of("2024-06-01")
    # no food/energy codes present
    for banned in ("SAF1", "SETB", "SETB01", "SEHF", "SEHF01", "SEHE"):
        assert banned not in part
    wsum = sum(RI.get(c, 0) for c in part)
    assert 78.0 < wsum < 82.0            # core ~ 80% of CPI


def test_headline_reconstruction_meets_1bp_under_current_methodology():
    """Headline NSA reconstructed from official majors + published RIs matches official
    All items NSA to <=1 bp for 2023+ (BLS's current annual-weight regime)."""
    r = A.reconstruction_error("headline", seasonal="NSA")
    assert r["n_components"] == 8
    assert r["mae_2023plus_bp"] is not None and r["mae_2023plus_bp"] <= 1.0
    # pre-2023 biennial-weight era is looser (published-RI approximation) -> full-window worse
    assert r["mae_bp"] > r["mae_2023plus_bp"]


def test_pre2023_biennial_era_is_the_residual():
    """The reconstruction gap lives in 2021-2022 (biennial weights + inflation surge), not
    the current regime — 2021 error is materially larger than 2024."""
    r = A.reconstruction_error("headline", seasonal="NSA")
    assert r["mae_by_year"][2021] > 3 * r["mae_by_year"][2024]


def test_sa_conversion_overhead_is_negligible():
    """Reconstructing in SA space (aggregating published SA majors, which embed the harvested
    stratum factors) is as accurate as NSA — the aggregate SA-conversion overhead is <0.5 bp."""
    for agg in ("headline", "core"):
        nsa = A.reconstruction_error(agg, seasonal="NSA")["mae_2023plus_bp"]
        sa = A.reconstruction_error(agg, seasonal="SA")["mae_2023plus_bp"]
        assert abs(sa - nsa) < 0.5
