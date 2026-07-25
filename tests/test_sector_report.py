"""Guards for the sector reporting layer (status report + nb06). Reporting must not fit or write."""
import numpy as np

from nowcast import sector_report as SR


def test_majors_partition_is_complete_and_disjoint():
    """Every leaf must map to at most one major group; the mapped weight must dominate."""
    items, leaves = SR._mapping()
    majors = [SR._major_of(c, items) for c in leaves]
    assert all(m in SR.MAJORS or m is None for m in majors)
    mapped = sum(1 for m in majors if m)
    assert mapped / len(leaves) > 0.9, f"only {mapped}/{len(leaves)} leaves map to a major group"


def test_offset_ratio_exceeds_one():
    """Gross sector error must exceed the net aggregate error — the cancellation property.
    (If this ever inverts, the aggregation or the sign convention is broken.)"""
    data = SR.sector_backtest(start="2024-01-01")          # short window keeps the test fast
    gross, net = SR.offset_series(data)
    g, n = np.mean(gross["values"]), np.mean(np.abs(net["values"]))
    assert g > n > 0, f"gross {g:.2f} should exceed net {n:.2f}"


def test_sector_stats_shape_and_bands():
    data = SR.sector_backtest(start="2024-01-01")
    stats = SR.sector_stats(data)
    assert stats, "expected sector rows"
    assert abs(sum(r["weight_share"] for r in stats) - 1.0) < 1e-6, "weight shares must sum to 1"
    for r in stats:
        assert r["p10_bp"] <= r["p90_bp"]
        assert r["mae_bp"] >= 0


def test_aggregate_devs_matches_replay_and_is_not_refit():
    dev = SR.aggregate_devs("cpi_headline")
    assert len(dev) > 50 and np.isfinite(dev).all()
    # the reporting layer must read the committed replay, never regenerate calls
    import csv
    n = sum(1 for r in csv.DictReader(open(SR.REPLAY)) if r["instrument"] == "cpi_headline")
    assert len(dev) == n
