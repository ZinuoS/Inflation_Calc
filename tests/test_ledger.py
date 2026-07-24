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
