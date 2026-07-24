"""H11 shadow-evaluation guards. The point of these tests is that the H11 harness cannot cheat:
the seasonal mean must be causal, and the AR fit must never see the fold it predicts."""
import numpy as np
import pytest

from nowcast import h11


def test_seasonal_mean_is_causal():
    """s_t must use only prior-YEAR same-calendar-month values, never month t itself."""
    months = [f"{y}-{m:02d}-01" for y in range(2010, 2020) for m in range(1, 13)]
    y = np.arange(len(months), dtype=float) / 1000.0
    s, d = h11.seasonal_and_deviation(months, y)
    i = months.index("2019-06-01")
    prior = [y[months.index(f"{yy}-06-01")] for yy in range(2011, 2019)]
    assert s[i] == pytest.approx(float(np.mean(prior)))
    assert d[i] == pytest.approx(y[i] - s[i])


def test_seasonal_mean_undefined_without_history():
    months = [f"2010-{m:02d}-01" for m in range(1, 13)]
    s, _ = h11.seasonal_and_deviation(months, np.ones(12))
    assert np.isnan(s).all(), "no prior-year history => seasonal mean must be undefined, not 0"


def test_ar_fit_respects_embargo_and_never_reads_the_target():
    """The AR fit for t must exclude [t-EMBARGO, t]; poisoning that window must not change it."""
    rng = np.random.default_rng(0)
    d = rng.normal(size=200)
    t = 150
    clean = h11._fit_predict_ar(d, 3, t)
    poisoned = d.copy()
    poisoned[t - h11.EMBARGO:t + 1] = 1e6          # target + embargoed tail
    # lags feeding the prediction come from d[t-k:t]; keep those, poison only the fit window
    poisoned[t - 3:t] = d[t - 3:t]
    assert clean is not None
    assert h11._fit_predict_ar(poisoned, 3, t) == pytest.approx(clean, rel=1e-9)


def test_walkforward_starts_after_min_train():
    months = [f"{y}-{m:02d}-01" for y in range(2000, 2020) for m in range(1, 13)]
    rng = np.random.default_rng(1)
    y = rng.normal(scale=0.01, size=len(months))
    i, base, hh, act = h11.walkforward(months, y, 2)
    assert len(i) > 0
    assert i.min() >= h11.MIN_TRAIN
    assert len(base) == len(hh) == len(act) == len(i)


def test_frozen_config_untouched_by_h11():
    """H11 is a SHADOW evaluation: importing/running it must not mutate the frozen baseline."""
    import yaml
    cfg = yaml.safe_load((h11.REPO / "config" / "component_models.yaml").read_text())
    assert cfg["default"]["model"] == "seasonal_ar"
    assert cfg["default"]["seasonal_years"] == 8
    assert cfg["default"].get("ar_lags", 1) == 1
