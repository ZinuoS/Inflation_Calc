"""Golden-fixture PARSE tests for Session-2B proxy sources.

Each source's deterministic parse(raw_bytes, spec, observed_date) is run against a
saved raw sample (pipelines/{source}/golden/raw_sample.*) and checked against the
expected uniform staged rows. These are offline and always run (the naru CSV->DB
load is separately golden-tested per the shared proxy_loader artifact).
"""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

PIPELINES = Path(__file__).parent.parent / "pipelines"
sys.path.insert(0, str(PIPELINES))


def _load_source(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_fetch", PIPELINES / name / "fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = yaml.safe_load((PIPELINES / name / "spec.yaml").read_text())
    return mod, cfg


# ---------- zori ----------

def test_zori_parse_extracts_us_national_monthly():
    mod, cfg = _load_source("zori")
    raw = (PIPELINES / "zori" / "golden" / "raw_sample.csv").read_bytes()
    rows = mod.parse(raw, cfg, observed_date="2026-07-19")
    assert len(rows) == 3  # US row, 3 month columns
    assert {r["series_key"] for r in rows} == {"US"}
    assert {r["source"] for r in rows} == {"zori"}
    assert {r["vintage_status"] for r in rows} == {"revised_latest_only"}
    assert rows[0]["period"] == "2015-01-01"  # month-end 2015-01-31 -> first-of-month
    assert rows[0]["value"] == "1169.7142129767246"
    assert rows[0]["frequency"] == "monthly"


# ---------- eia_gasoline (FRED-delivered EIA weekly) ----------

def test_eia_gasoline_parse_weekly():
    import json

    mod, cfg = _load_source("eia_gasoline")
    raw = json.loads((PIPELINES / "eia_gasoline" / "golden" / "raw_sample.json").read_bytes())
    obs = [(o["date"], o["value"]) for o in raw["observations"] if o["value"] != "."]
    rows = mod.to_staged(obs, cfg)
    assert len(rows) == 2  # the "." missing value is dropped upstream
    assert rows[0]["frequency"] == "weekly"
    assert rows[0]["period"] == "1990-08-20"
    assert rows[0]["value"] == "1.191"
    assert rows[0]["vintage_status"] == "unrevised"
    assert rows[0]["observed_date"] == "1990-08-20"  # knowable on its week date


# ---------- eia_heating_oil (FRED-delivered EIA spot) ----------

def test_eia_heating_oil_parse():
    import json

    mod, cfg = _load_source("eia_heating_oil")
    raw = json.loads((PIPELINES / "eia_heating_oil" / "golden" / "raw_sample.json").read_bytes())
    obs = [(o["date"], o["value"]) for o in raw["observations"] if o["value"] != "."]
    rows = mod.to_staged(obs, cfg)
    assert rows and rows[0]["frequency"] == cfg["frequency"]
    assert rows[0]["vintage_status"] == "unrevised"


# ---------- atlanta_fed_wage (FRED-delivered, monitor) ----------

def test_atlanta_fed_wage_parse():
    import json

    mod, cfg = _load_source("atlanta_fed_wage")
    raw = json.loads((PIPELINES / "atlanta_fed_wage" / "golden" / "raw_sample.json").read_bytes())
    obs = [(o["date"], o["value"]) for o in raw["observations"] if o["value"] != "."]
    rows = mod.to_staged(obs, cfg, observed_date="2026-07-19")
    assert len(rows) == 2
    assert rows[0]["frequency"] == "monthly"
    assert rows[0]["vintage_status"] == "revised_latest_only"
    assert rows[0]["observed_date"] == "2026-07-19"  # restated -> pull date, not period


# ---------- indeed_wage (long CSV, US filter, monitor) ----------

def test_indeed_wage_parse_filters_us_and_parses_month():
    mod, cfg = _load_source("indeed_wage")
    raw = (PIPELINES / "indeed_wage" / "golden" / "raw_sample.csv").read_bytes()
    rows = mod.parse(raw, cfg, observed_date="2026-07-19")
    assert len(rows) == 2  # only the US rows, not Canada
    assert {r["series_key"] for r in rows} == {"US_posted_wage_growth_yoy"}
    assert rows[0]["period"] == "2019-01-01"  # "Jan-19" -> first-of-month
    assert rows[0]["value"] == "0.03626943"
    assert rows[0]["vintage_status"] == "revised_latest_only"


# ---------- bls_cpi_series (Group C, official flat files) ----------

def test_bls_cpi_parse_filters_codes_and_drops_m13():
    mod, cfg = _load_source("bls_cpi_series")
    raw = (PIPELINES / "bls_cpi_series" / "golden" / "raw_sample.txt").read_text()
    rows = mod.parse_flat(raw, {"SEHA"}, cfg, observed_date="2026-07-19")
    # 2 SA + 2 NSA monthly rows; the M13 annual-average row is dropped
    assert len(rows) == 4
    assert {r["seasonal"] for r in rows} == {"SA", "NSA"}
    assert {r["item_code"] for r in rows} == {"SEHA"}
    sa = [r for r in rows if r["seasonal"] == "SA"][0]
    assert sa["series_id"] == "CUSR0000SEHA"
    assert sa["period"] == "1981-01-01"  # year 1981 + M01
    assert sa["value"] == "84.7"
    # only requested codes come through: SEHA yields rows, SETB01 (also in sample) is
    # excluded when not requested; a code absent from the sample yields nothing
    assert all(r["item_code"] == "SEHA" for r in rows)  # SETB01 line filtered out
    assert mod.parse_flat(raw, {"SAF11"}, cfg, observed_date="2026-07-19") == []


# ---------- ppi_series (Group C, BLS API) ----------

def test_ppi_parse_seasonal_by_prefix_and_drops_invalid():
    import json

    mod, cfg = _load_source("ppi_series")
    payload = json.loads((PIPELINES / "ppi_series" / "golden" / "raw_sample.json").read_bytes())
    rows = mod.parse_bls(payload, cfg, observed_date="2026-07-19")
    # WPSFD4 M01 (M13 dropped) + PCU M01 ("-" M02 dropped) = 2 rows
    assert len(rows) == 2
    by = {r["series_id"]: r for r in rows}
    assert by["WPSFD4"]["seasonal"] == "SA"       # WPS -> SA
    assert by["PCU622110622110"]["seasonal"] == "NSA"  # PCU -> NSA
    assert by["WPSFD4"]["period"] == "2024-01-01"
    assert by["WPSFD4"]["source"] == "ppi"


def test_official_key_index_created_before_bulk_load(tmp_path):
    """CARRY 2 / naru#7: a from-scratch rebuild must create the official_current key
    index BEFORE the bulk load, deterministically (no runbook step). Assert the shim
    creates the table + key index on a fresh DB."""
    import sqlite3

    mod, _ = _load_source("bls_cpi_series")
    db = tmp_path / "fresh.sqlite"
    mod.ensure_indexed_official_table(db)
    conn = sqlite3.connect(db)
    idx = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='official_current'")}
    conn.close()
    assert "ix_official_key" in idx  # supersede UPDATE probe is O(log n), not O(n)


# ---------- nadac (Group A / Task 3, placeholder matched-model index) ----------

def test_nadac_matched_model_index():
    mod, cfg = _load_source("nadac")
    raw = (PIPELINES / "nadac" / "golden" / "raw_sample.csv").read_bytes()
    acc = {}
    mod.monthly_ndc_means(raw, cfg["columns"], acc, cfg["date_format"])
    # 2 NDCs x 2 months = 4 (ndc, month) buckets
    assert len(acc) == 4
    # both drugs rose +10% -> geomean-of-relatives = 1.10 -> index 100 -> 110
    cfg = {**cfg, "basket_rule": {**cfg["basket_rule"], "min_matched_ndcs": 1}}
    rows, skipped = mod.build_index(acc, cfg)
    assert [r["period"] for r in rows] == ["2024-01-01", "2024-02-01"]
    assert float(rows[0]["value"]) == pytest.approx(100.0)
    assert float(rows[1]["value"]) == pytest.approx(110.0)
    assert rows[0]["vintage_status"] == "unrevised"
