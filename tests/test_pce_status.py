"""Guards for the daily PCE status report. Its cardinal rule: it must NEVER adjudicate."""
import datetime as dt

from nowcast import pce_status as PS


def test_realized_status_is_data_driven_and_currently_pending():
    """Landed-ness is decided by the DB, not the calendar. Before 2026-07-30 there is no value."""
    status, val = PS.realized_status()
    assert status in ("pending", "published")
    if status == "pending":
        assert val is None


def test_report_never_writes_a_realized_value():
    """The rendered report must show the ledger's own realized field, not invent one."""
    from nowcast import ledger as L
    row = L.find_row(PS.INSTRUMENT, PS.REF_MONTH)
    txt = PS.render(as_of=dt.date(2026, 7, 25))
    status, _ = PS.realized_status()
    if status == "pending":
        assert "pending" in txt and "STANDING PREDICTION" in txt
        assert row["realized_bp"] == "—", "ledger realized must still be unpopulated"
    # the frozen call and hash must appear verbatim — the report cannot restate the call
    assert row["call_bp"] in txt and row["row_hash"] in txt


def test_daily_log_is_idempotent_per_date(tmp_path, monkeypatch):
    monkeypatch.setattr(PS, "LOG", tmp_path / "log.csv")
    rec = {"check_date": "2026-07-25", "days_to_print": 5, "realized_status": "pending",
           "call_bp": "+7.6", "ledger_hash": "abc", "note": "x"}
    assert PS.append_log(rec) is True
    assert PS.append_log(rec) is False, "same-day re-run must not duplicate"
    assert len(PS.read_log()) == 1


def test_confidence_band_is_sane():
    h = PS.band_from_history()
    assert h["n"] > 20
    assert h["p10"] < 0 < h["p90"], "an 80% error band should straddle zero"
    assert 0 < h["mae"] < 50
    assert abs(h["bias"]) < 5, "Instrument A is documented as ~unbiased"


def test_implied_yoy_is_a_deterministic_transform_not_a_new_claim():
    """YoY must follow mechanically from the MoM call + published levels (rule 8: never a target)."""
    y = PS.implied_yoy(7.6)
    assert y is not None
    # reconstruct by hand from the reported levels
    expect = (y["prev_level"] * (1 + 7.6 / 1e4) / y["base_level"] - 1) * 100
    assert abs(y["implied_yoy_pct"] - expect) < 1e-9
    # a bigger MoM call must imply a bigger YoY, and the map must be monotone
    assert PS.implied_yoy(20.0)["implied_yoy_pct"] > y["implied_yoy_pct"] > PS.implied_yoy(-5.0)["implied_yoy_pct"]


def test_report_states_both_conventions_and_refuses_yoy_scoring():
    txt = PS.render(as_of=dt.date(2026, 7, 25))
    assert "percentage points (pp)" in txt          # release convention is primary
    assert "MoM — the scored quantity" in txt
    assert "a scored target" in txt                 # YoY heading marks it context-only
    assert "never scored" in txt                    # and the body says so explicitly
    assert "rule 8" in txt                          # the reason is stated, not implied
