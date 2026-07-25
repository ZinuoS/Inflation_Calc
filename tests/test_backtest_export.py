"""Guards for the backtest CSV: unit discipline, basis labelling, and no imputed consensus."""
import csv

from nowcast import backtest_export as X


def test_csv_is_self_consistent_at_published_precision():
    """A reader must be able to recompute every error column FROM the file and get the printed
    number. (Formatting each column from full precision independently breaks this.)"""
    rows = list(csv.DictReader(open(X.OUT)))
    assert len(rows) > 150
    for r in rows:
        ours, act = float(r["our_call_pp"]), float(r["actual_pp"])
        assert abs((ours - act) - float(r["our_err_pp"])) < 1e-9, r
        # pp magnitudes: a monthly MoM print never exceeds a few pp
        assert abs(ours) < 5 and abs(act) < 5, f"looks like bp not pp: {r}"
        if r["consensus_pp"]:
            c = float(r["consensus_pp"])
            assert abs((c - act) - float(r["consensus_err_pp"])) < 1e-9, r
            assert abs((ours - c) - float(r["divergence_pp"])) < 1e-9, r
            # consensus is the ROUNDED market median -> multiple of 0.1
            assert abs(round(c / 0.1) * 0.1 - c) < 1e-9, r


def test_basis_is_labelled_on_every_row():
    """CPI is NSA-native and must be flagged as converted; PCE is natively SA."""
    for r in csv.DictReader(open(X.OUT)):
        if r["instrument"].startswith("cpi"):
            assert r["our_call_basis"] == "sa_converted_from_nsa"
        else:
            assert r["our_call_basis"] == "native_sa"


def test_consensus_cells_are_cited_or_blank():
    """A consensus number without its article is an uncited fact; a gap must be truly empty."""
    for r in csv.DictReader(open(X.OUT)):
        if r["consensus_pp"]:
            assert r["consensus_source_url"].startswith("http"), r
            assert r["consensus_article_date"], r
        else:
            assert r["consensus_err_pp"] == "" and r["divergence_pp"] == "", r
            assert "gap" in r["notes"]


def test_summary_matches_session9_verdicts():
    """Head-to-head must reproduce the recorded result: headline ~parity, core/PCE consensus ahead."""
    s = X.summary()
    assert s["cpi_headline"]["n"] == 30
    assert abs(s["cpi_headline"]["our_mae_pp"] - s["cpi_headline"]["consensus_mae_pp"]) < 0.005
    assert s["cpi_core"]["consensus_mae_pp"] < s["cpi_core"]["our_mae_pp"]
    assert s["pce_core"]["consensus_mae_pp"] < s["pce_core"]["our_mae_pp"]
