"""Tests for bls_cpi_weights parse + weights.py as-of serving (Session 3A, Task 2)."""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
PIPE = REPO / "pipelines" / "bls_cpi_weights"
DB = REPO / "data" / "db" / "nowcast.sqlite"
sys.path.insert(0, str(REPO / "pipelines"))


def _fetch_mod():
    spec = importlib.util.spec_from_file_location("bcw_fetch", PIPE / "fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_table1_panel_only_and_all_items():
    mod = _fetch_mod()
    name2code = {"rent of primary residence": "SEHA", "gasoline (all types)": "SETB01"}
    rows = mod.parse_table1(PIPE / "golden" / "raw_sample.xlsx", 2024, name2code)
    by = {r["item_code"]: r for r in rows}
    assert by["SA0"]["weight_cpi_u"] == "100.000"      # 'All items' -> SA0
    assert by["SEHA"]["weight_cpi_u"] == "7.840"
    assert by["SETB01"]["weight_cpi_u"] == "2.900"
    assert all(r["weight_year"] == "2024" for r in rows)
    # the post-'Special aggregate indexes' row (SA0L1E) must NOT appear (panel stops there)
    assert "SA0L1E" not in by and len(rows) == 3


@pytest.mark.skipif(not DB.exists(), reason="nowcast.sqlite not built")
def test_weights_as_of_vintaged_and_bounded():
    from nowcast.weights import OutOfWeightCoverage, coverage_years, weights_as_of

    cov = coverage_years(DB)
    assert {2020, 2025} <= cov
    for y in cov:
        w = weights_as_of(f"{y}-06-01", db_path=DB)
        assert abs(w["SA0"] - 100.0) < 1e-6                 # all items = 100
        assert abs(sum(v for k, v in w.items() if k in
                       ("SAF", "SAH", "SAA", "SAT", "SAM", "SAR", "SAE", "SAG")) - 100.0) < 0.05
    # weights are vintaged (differ across years) and out-of-coverage refuses
    assert weights_as_of("2020-06-01", db_path=DB)["SEHA"] != weights_as_of("2025-06-01", db_path=DB)["SEHA"]
    for bad in ("2019-06-01", "2026-06-01"):
        with pytest.raises(OutOfWeightCoverage):
            weights_as_of(bad, db_path=DB)
