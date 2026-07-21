"""Seasonal (X-13) tests — skip cleanly if x13as is not installed (Session 3A, Task 3)."""
import numpy as np
import pandas as pd
import pytest

from nowcast import seasonal

pytestmark = pytest.mark.skipif(seasonal.x13_binary() is None, reason="x13as not on PATH/X13PATH")


def test_seasonally_adjust_removes_seasonality():
    idx = pd.date_range("2010-01-01", periods=120, freq="MS")
    seas = pd.Series([1, .97, 1.03, 1.06, 1.04, .96, .94, .95, 1.0, 1.05, 1.07, .99] * 10, index=idx)
    trend = pd.Series([1.002 ** i for i in range(120)], index=idx)
    noise = pd.Series(1 + np.random.default_rng(0).normal(0, 0.01, 120), index=idx)
    y = 100 * trend * seas * noise
    sa = seasonal.seasonally_adjust(y)
    assert sa.pct_change().std() < y.pct_change().std() / 3  # seasonality largely removed


def test_x13_unavailable_raises_when_missing(monkeypatch):
    monkeypatch.setattr(seasonal, "x13_binary", lambda: None)
    with pytest.raises(seasonal.X13Unavailable):
        seasonal.seasonally_adjust(pd.Series([1.0, 2.0], index=pd.date_range("2020-01-01", periods=2, freq="MS")))
