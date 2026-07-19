"""Golden-fixture PARSE tests for Session-2B proxy sources.

Each source's deterministic parse(raw_bytes, spec, observed_date) is run against a
saved raw sample (pipelines/{source}/golden/raw_sample.*) and checked against the
expected uniform staged rows. These are offline and always run (the naru CSV->DB
load is separately golden-tested per the shared proxy_loader artifact).
"""

import importlib.util
import sys
from pathlib import Path

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
