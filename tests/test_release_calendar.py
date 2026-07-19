"""Offline tests for the release_calendar normalization (the leakage firewall).

Network-free: exercises fetch.py's pure helpers (reference-month mapping,
earliest-wins collision resolution, gap detection, provisional flagging) with
synthetic release dates. The live pull is validated at CHECKPOINT 1, not here.
"""

import datetime as dt
import importlib.util
from pathlib import Path

import pandas as pd
import pytest
import yaml

PIPE = Path(__file__).parent.parent / "pipelines" / "release_calendar"


def _load_fetch():
    spec = importlib.util.spec_from_file_location("rc_fetch", PIPE / "fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fetch = _load_fetch()
SPEC = yaml.safe_load((PIPE / "spec.yaml").read_text())


def _prov(prints):
    return [{"print": p, "source_url": f"https://fred/{p}"} for p in prints]


# ---------- reference-month mapping ----------


@pytest.mark.parametrize("release,expected", [
    ("2020-01-15", dt.date(2019, 12, 1)),   # January release -> previous December
    ("2020-02-20", dt.date(2020, 1, 1)),
    ("2020-12-10", dt.date(2020, 11, 1)),
    ("2020-03-31", dt.date(2020, 2, 1)),
])
def test_reference_month(release, expected):
    assert fetch._reference_month(dt.date.fromisoformat(release)) == expected


# ---------- collision: earliest wins, logged ----------


def test_collision_keeps_earliest_and_logs(tmp_path):
    per_print = {"CPI": ["2020-02-25", "2020-02-18"]}  # both -> ref 2020-01
    csv_path, exc = fetch._normalize(SPEC, per_print, tmp_path, _prov(["CPI"]))
    rows = list(pd.read_csv(csv_path).itertuples())
    assert len(rows) == 1
    assert rows[0].release_date == "2020-02-18"          # earliest kept
    assert len(exc["collisions"]) == 1
    assert exc["collisions"][0]["also_mapped_here"] == ["2020-02-25"]


# ---------- gap detection ----------


def test_gap_is_detected_and_logged(tmp_path):
    per_print = {"CPI": ["2020-02-18", "2020-04-15"]}    # refs 2020-01, 2020-03 -> gap 2020-02
    _, exc = fetch._normalize(SPEC, per_print, tmp_path, _prov(["CPI"]))
    missing = [g["missing_reference_period"] for g in exc["gaps"]]
    assert "2020-02-01" in missing


# ---------- provisional flagging (PCE) ----------


def test_pce_marked_provisional_others_not(tmp_path):
    per_print = {"CPI": ["2020-02-18"], "PCE": ["2020-02-27"]}
    csv_path, _ = fetch._normalize(SPEC, per_print, tmp_path, _prov(["CPI", "PCE"]))
    df = pd.read_csv(csv_path).set_index("print")
    assert df.loc["PCE", "reference_period_basis"] == "provisional_pending_vintage"
    assert df.loc["CPI", "reference_period_basis"] == "release_month_minus_1"


# ---------- time convention imposed, url carries no api key ----------


def test_time_convention_and_redacted_url(tmp_path):
    csv_path, _ = fetch._normalize(SPEC, {"CPI": ["2020-02-18"]}, tmp_path, _prov(["CPI"]))
    row = pd.read_csv(csv_path).iloc[0]
    assert row["release_datetime_et"] == "2020-02-18T08:30:00"
    assert row["release_time_basis"] == "convention_0830ET"


def test_redact_strips_api_key():
    red = fetch._redact("https://api.stlouisfed.org/x?release_id=10&api_key=SECRET&file_type=json")
    assert "SECRET" not in red and "api_key=REDACTED" in red
