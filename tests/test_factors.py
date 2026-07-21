"""Tests for src/nowcast/factors.py — the Checkpoint-2 reroute (NSA + harvested BLS
factors). Uses the live governed DB (read-only), like test_seasonal."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from nowcast import factors

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")


def test_implied_factor_is_seasonal_and_signed():
    # Gasoline: summer NSA > SA (factor > 1), winter NSA < SA (factor < 1).
    jul = factors.implied_factor("SETB01", "2024-07-01")
    jan = factors.implied_factor("SETB01", "2024-01-01")
    assert 1.02 < jul < 1.10
    assert 0.90 < jan < 0.98


def test_series_alias_and_naming():
    assert factors.sa_series("SAA") == "CPIAPPSL"      # ALFRED-aliased aggregate
    assert factors.sa_series("SETB01") == "CUSR0000SETB01"
    assert factors.nsa_series("SETB01") == "CUUR0000SETB01"


def test_published_factor_matches_first_release_implied():
    """The harvested published projected factor IS the factor BLS applies at first
    release: NSA/SA_firstrelease should equal it to rounding (< 1 bp), proving the
    harvest identifies the applied factor (not a hindsight-revised one)."""
    for m in ["2022-07-01", "2023-05-01", "2024-09-01", "2025-07-01"]:
        pub = factors.published_factor_asof("SETB01", m, "2026-01-01")
        fr = factors.implied_factor("SETB01", m, basis="first_release")
        assert pub is not None and fr is not None
        assert abs(pub - fr) / fr < 1e-4  # < 1 bp


def test_published_factor_respects_publication_date():
    """A year-Y factor must not be visible before it was introduced (its published_asof =
    the Jan-Y CPI release). Asking as-of just before that date falls back to a PRIOR
    year's factor (different value), never the not-yet-published one."""
    # 2025 factors introduced 2025-02-12; before it, July lookup must not return the 2025 value.
    before = factors.published_factor_asof("SETB01", "2025-07-01", "2025-02-01")
    at = factors.published_factor_asof("SETB01", "2025-07-01", "2026-01-01")
    assert at is not None
    # before introduction we either get None or a fallback that is NOT the 2025-07 value
    assert before is None or abs(before - at) > 1e-9


def test_indirectly_adjusted_stratum_has_no_direct_factor():
    # Apparel (SAA) is indirectly seasonally adjusted -> not in the published factor files.
    assert factors.published_factor_asof("SAA", "2024-07-01", "2026-01-01") is None


def test_conversion_floor_clean_months_are_essentially_zero():
    """Option (a): with harvested published factors, the SA-conversion floor for the
    clean months (Mar-Dec, both endpoints in-year) is rounding-level (< 1 bp), far below
    the retired 10 bp gate and the ~15 bp carry-forward floor."""
    for code in ["SETB01", "SETA02", "SETG01"]:
        res = factors.factor_conversion_error(code, years=8)
        assert res["n_clean"] > 30
        assert res["mae_clean_bp"] is not None and res["mae_clean_bp"] < 1.0
        # the boundary (Jan/Feb annual seam) is genuinely larger — the irreducible residual
        assert res["mae_boundary_bp"] > res["mae_clean_bp"]
