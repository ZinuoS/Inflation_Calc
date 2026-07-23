"""Tests for src/nowcast/voc.py (Session 4, Task 3, H7)."""
from pathlib import Path
import numpy as np
import pytest
from nowcast import voc

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")


def test_feature_matrix_shape_and_finiteness():
    months = [f"2018-{m:02d}-01" for m in range(1, 13)] + [f"2019-{m:02d}-01" for m in range(1, 13)]
    X, y, names, keep = voc.feature_matrix(months)
    assert X.shape[1] == len(names) == 17 and len(y) == X.shape[0]
    assert np.isfinite(X).all() and np.isfinite(y).all()


def test_walkforward_is_leakage_safe_intercept_in():
    # a pure-noise target must not be "predicted" well OOS (guards against leakage)
    rng = np.random.default_rng(0); X = rng.normal(size=(80, 5)); y = rng.normal(size=80)
    pred = voc._walkforward(X, y, lambda a, b, c: voc._ridge(a, b, c, 1.0)[0], min_train=40, embargo=2)
    assert voc.mae(pred, y) > 0.5 * np.mean(np.abs(y))   # no spurious skill on noise
