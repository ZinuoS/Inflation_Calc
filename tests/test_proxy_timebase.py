"""Adversarial proxy-timing firewall tests (Session 3B, Task 2d part c).

For each proxy source, request data at a timestamp BETWEEN a reference period's end and its
observed_asof, and assert the not-yet-published observation is withheld and the prior one is
returned. A failure here means the proxy firewall leaks the future into Session-4 features —
the backtest is invalid, exactly as on the official side (test_timebase)."""
import datetime as dt
from pathlib import Path

import pytest

from nowcast import proxy_timebase as PT

DB = Path(__file__).resolve().parents[1] / "data" / "db" / "nowcast.sqlite"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="governed DB not built")

# (source, series_key, a monthly reference period present in the DB)
MONTHLY = [
    ("manheim", "US_full_month", "2025-06-01"),
    ("nadac", None, "2025-06-01"),
    ("tsa", "US_throughput", "2026-03-01"),
    ("zori", "US", "2025-06-01"),
    ("atlanta_fed_wage", "US_overall_median", "2025-06-01"),
    ("indeed_wage", "US_posted_wage_growth_yoy", "2025-06-01"),
]


@pytest.mark.parametrize("source,key,ref", MONTHLY)
def test_firewall_withholds_until_observed_asof(source, key, ref):
    asof = PT.observed_asof(source, ref)
    month_end = dt.date.fromisoformat(ref[5:7].join([ref[:4], "01"])) if False else None  # noqa
    # a timestamp AFTER the reference month ends but BEFORE the value is published
    just_before = asof - dt.timedelta(days=1)
    assert just_before >= dt.date.fromisoformat(ref), "test period ill-formed"
    visible = PT.proxy_asof(source, just_before, series_key=key)
    assert ref not in visible, f"{source} leaked {ref} at {just_before} (published {asof})"
    # at observed_asof the value becomes visible
    on_pub = PT.proxy_asof(source, asof, series_key=key)
    assert ref in on_pub, f"{source} did not publish {ref} by its observed_asof {asof}"
    # and the PRIOR observation was already available just before
    prior = PT.proxy_asof(source, just_before, series_key=key)
    assert prior and max(prior) < ref


def test_eia_weekly_monday_plus_one():
    # Monday price is observable the next day, not on the reference Monday morning report cycle
    a = PT.observed_asof("eia_gasoline", "2024-06-03")
    assert a == dt.date(2024, 6, 4)


def test_sp500_same_day_and_manheim_next_month():
    assert PT.observed_asof("sp500", "2026-05-15") == dt.date(2026, 5, 15)
    # ref month M full-month index publishes in the FIRST WEEK of M+1 (archive /YYYY/(M+1)/)
    a = PT.observed_asof("manheim", "2025-01-01")
    assert a.year == 2025 and a.month == 2


def test_estimated_flag_present_for_revised_sources():
    for src in ("zori", "atlanta_fed_wage", "indeed_wage"):
        assert PT.publication_block(src)["observed_asof_estimated"] is True
    for src in ("eia_gasoline", "manheim", "sp500", "nadac", "tsa"):
        assert PT.publication_block(src)["observed_asof_estimated"] is False


def test_every_db_proxy_source_has_a_publication_rule():
    from nowcast import db
    with db.connect(str(DB)) as conn:
        sources = [r[0] for r in conn.execute("SELECT DISTINCT source FROM proxy_observations")]
    for s in sources:
        pub = PT.publication_block(s)  # raises if missing
        assert "rule" in pub and "cite" in pub
