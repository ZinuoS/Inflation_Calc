"""Tests for src/nowcast/event_study.py (Session 6, Task 1) — replay consistency + freeze."""
import datetime as dt
from pathlib import Path
import pytest
from nowcast import component_models as CM
from nowcast import event_study as ES, intramonth

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")


def test_freeze_equivalence_t0_equals_t4():
    """The freeze claim: nothing useful arrives between T-4 and T-0, so the calls are identical.
    If this ever fails, the availability calendar's 'last useful update' is wrong."""
    cfg = CM._cfg()
    import sqlite3
    c = sqlite3.connect(str(DB))
    for m in ("2026-05-01", "2026-06-01"):
        rel = intramonth._release_date(c, m)
        t0 = CM.forecast_aggregate_nsa(m, rel, "headline", cfg)["forecast_mom"]
        t4 = CM.forecast_aggregate_nsa(m, rel - dt.timedelta(days=4), "headline", cfg)["forecast_mom"]
        assert abs(t0 - t4) < 1e-12
    c.close()


def test_replay_record_is_pure_and_complete():
    """A replay record carries the call, realized, deviation, benchmarks and the as-of stamps —
    everything needed to audit the call without re-running it."""
    r = ES.replay_cpi("2026-05-01", "cpi_headline")
    assert r is not None
    for k in ("call_bp", "realized_bp", "deviation_bp", "asof", "effective_asof", "frozen", "attribution"):
        assert k in r
    assert r["frozen"] is True                      # T-3 as-of is past the T-4 freeze -> clamped
    assert abs(r["deviation_bp"] - (r["call_bp"] - r["realized_bp"])) < 0.02
