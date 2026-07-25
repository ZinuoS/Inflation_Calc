"""Pristine ledger integrity (Session 6, Task 3) — append-only is ENFORCED, not requested."""
from pathlib import Path
import pytest
from nowcast import ledger

pytestmark = pytest.mark.skipif(not ledger.LEDGER.exists(), reason="ledger not seeded")


def test_committed_ledger_is_intact():
    """Every row's immutable fields must still hash to its recorded row_hash."""
    assert ledger.verify() == [], f"ledger tampered: {ledger.verify()}"


def test_editing_an_immutable_field_is_detected():
    rows = ledger.read_rows()
    assert rows, "ledger has no rows"
    tampered = dict(rows[0]); tampered["call_bp"] = "+99.9"        # retroactively 'improve' a call
    assert ledger.row_hash(tampered) != tampered["row_hash"]        # detected


def test_populating_realized_does_not_change_the_hash():
    """Populating realized/deviation/verdict is legal and must NOT alter the row hash."""
    r = dict(ledger.read_rows()[0])
    before = ledger.row_hash(r)
    r["realized_bp"], r["deviation_bp"], r["verdict"] = "+12.3", "-1.0", "within band"
    assert ledger.row_hash(r) == before


def test_a_call_is_written_once():
    rows = ledger.read_rows()
    keys = [(r["instrument"], r["ref_month"]) for r in rows]
    assert len(keys) == len(set(keys)), "duplicate call rows — a call must be written once"


def test_freeze_kind_key_allows_prefreeze_and_frozen_coexist(tmp_path, monkeypatch):
    """Carry-item (Aug-9 case): a pre-freeze T-21 call and a T-3 frozen call for the SAME
    (instrument, ref_month) must coexist as distinct rows with distinct valid hashes; the frozen
    append is idempotent; the T-21 row is never edited."""
    import importlib
    from nowcast import ledger as L
    ldg = tmp_path / "led.md"
    monkeypatch.setattr(L, "LEDGER", ldg)
    # T-21 pre-freeze call
    r1 = L.append_call({"instrument": "cpi", "ref_month": "2026-07-01", "as_of": "2026-07-22",
                        "frozen": False, "call_bp": -5.1, "band_bp": 12.0})
    # T-3 frozen call, same instrument/month — must NOT be deduped away
    r2 = L.append_call({"instrument": "cpi", "ref_month": "2026-07-01", "as_of": "2026-08-08",
                        "frozen": True, "call_bp": -4.4, "band_bp": 8.8})
    assert "skipped" not in r1 and "skipped" not in r2
    rows = L.read_rows()
    assert len(rows) == 2
    assert {L._freeze_kind(r) for r in rows} == {"prefreeze", "frozen"}
    assert rows[0]["row_hash"] != rows[1]["row_hash"]
    assert L.verify() == []
    # idempotent: re-appending the frozen call is skipped, T-21 row untouched
    again = L.append_call({"instrument": "cpi", "ref_month": "2026-07-01", "as_of": "2026-08-08",
                           "frozen": True, "call_bp": -4.4, "band_bp": 8.8})
    assert "skipped" in again
    assert len(L.read_rows()) == 2 and L.verify() == []
