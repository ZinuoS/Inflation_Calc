"""Session-1 gate tests for mapping/mapping.yaml (research plan Gate 1).

mapping.yaml is data, not code: these tests are the contract that keeps hand
edits and future regeneration honest. Tolerances reflect the 3-decimal rounding
of published BLS relative-importance weights.
"""
from pathlib import Path

import pytest
import yaml

MAPPING = Path(__file__).parent.parent / "mapping" / "mapping.yaml"

VALID_FORMULAS = {"jevons", "arithmetic", "none_unsampled"}
VALID_SOURCE_TYPES = {"cpi_relative", "ppi_relative", "bea_imputed"}
VALID_ALT_STATUS = {"build", "vendor_only", "excluded", "none"}
# per-node tolerance: children are each rounded to 3dp
CHILD_SUM_TOL = 0.011
TOTAL_TOL = 0.02


@pytest.fixture(scope="module")
def mapping():
    with open(MAPPING) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def cpi_items(mapping):
    return mapping["cpi"]["items"]


@pytest.fixture(scope="module")
def strata(cpi_items):
    return [d for d in cpi_items if d["is_stratum"]]


# ---------- weights sum within tolerance per level ----------

def test_top_level_weights_sum_to_100(cpi_items):
    total = sum(d["weight_cpi_u"] for d in cpi_items if d["indent"] == 1)
    assert abs(total - 100.0) <= TOTAL_TOL


def test_leaf_weights_sum_to_100(strata):
    total = sum(d["weight_cpi_u"] for d in strata)
    assert abs(total - 100.0) <= TOTAL_TOL


def test_children_sum_to_parent_weight(cpi_items):
    violations = []
    for parent in cpi_items:
        if parent["is_stratum"] or not parent["item_code"]:
            continue
        kids = [d for d in cpi_items if d["parent_code"] == parent["item_code"]]
        if not kids:
            continue
        s = sum(k["weight_cpi_u"] for k in kids)
        if abs(s - parent["weight_cpi_u"]) > CHILD_SUM_TOL:
            violations.append((parent["name"], parent["weight_cpi_u"], round(s, 3)))
    assert not violations, f"parent/child weight mismatches: {violations}"


# ---------- every stratum has formula + sa_flag ----------

def test_every_stratum_has_formula_and_sa_flag(strata):
    for s in strata:
        assert s.get("lower_level_formula") in VALID_FORMULAS, s["name"]
        assert isinstance(s.get("sa_flag"), bool), s["name"]


def test_published_strata_have_real_formula(strata):
    for s in strata:
        if s["published"]:
            assert s["lower_level_formula"] in ("jevons", "arithmetic"), s["name"]
        else:
            assert s["lower_level_formula"] == "none_unsampled", s["name"]


def test_series_id_consistent_with_sa_flag_and_code(strata):
    for s in strata:
        if not s["published"]:
            assert s["series_id"] is None, s["name"]
            continue
        prefix = "CUSR0000" if s["sa_flag"] else "CUUR0000"
        assert s["series_id"] == f"{prefix}{s['item_code']}", s["name"]


# ---------- every PCE component has a source ----------

def test_every_pce_component_has_source(mapping):
    for c in mapping["pce_bridge"]["components"]:
        assert c["source_type"] in VALID_SOURCE_TYPES, c["component"]
        if c["source_type"] == "bea_imputed":
            assert c["source_series"] is None, c["component"]
            assert c["scope_adjustment_note"], c["component"]
        else:
            assert isinstance(c["source_series"], list) and c["source_series"], c["component"]
        assert c["weight_source"], c["component"]
        assert isinstance(c["in_core"], bool), c["component"]
        assert c["confidence"] in ("high", "medium", "low"), c["component"]


# ---------- no orphan series ids ----------

def test_no_orphan_parent_codes(cpi_items):
    codes = {d["item_code"] for d in cpi_items if d["item_code"]} | {"SA0"}
    orphans = [d["name"] for d in cpi_items if d["parent_code"] not in codes]
    assert not orphans, f"nodes with unknown parent_code: {orphans}"


def test_no_orphan_bridge_references(mapping, cpi_items):
    cpi_codes = {d["item_code"] for d in cpi_items if d["item_code"]} | {"SA0"}
    ppi_ids = {f["series_id"] for f in mapping["ppi"]["pce_feeders"]}
    orphans = []
    for c in mapping["pce_bridge"]["components"]:
        for tok in c["source_series"] or []:
            if tok.startswith("PCU"):
                if tok not in ppi_ids:
                    orphans.append((c["component"], tok))
            elif tok not in cpi_codes:
                orphans.append((c["component"], tok))
    assert not orphans, f"bridge references unknown series: {orphans}"


def test_ppi_feeders_reference_bridge_components(mapping):
    bridge_ppi = {tok for c in mapping["pce_bridge"]["components"]
                  for tok in (c["source_series"] or []) if tok.startswith("PCU")}
    unused = [f["series_id"] for f in mapping["ppi"]["pce_feeders"]
              if f["series_id"] not in bridge_ppi]
    # P&C insurance feeder is intentionally monitor-only (bridge prices insurance as
    # a BEA margin imputation); anything else unused is an orphan.
    assert unused in ([], ["PCU524126524126"]), f"unused pce_feeders: {unused}"


# ---------- excluded sources have a proxy ----------

def test_excluded_or_vendor_only_have_proxy_or_explicit_carry(strata):
    bad = []
    for s in strata:
        alt = s["alt"]
        assert alt["alt_status"] in VALID_ALT_STATUS, s["name"]
        if alt["alt_status"] in ("excluded", "vendor_only"):
            has_proxy = alt["proxy_source"] is not None
            explicit_carry = "carry consensus" in (alt.get("note") or "").lower()
            if not (has_proxy or explicit_carry):
                bad.append(s["name"])
    assert not bad, f"excluded/vendor-only strata without proxy or explicit carry flag: {bad}"


def test_every_stratum_has_alt_block(strata):
    for s in strata:
        assert "alt" in s and "alt_status" in s["alt"] and "proxy_source" in s["alt"], s["name"]


# ---------- targets ----------

def test_all_d2_targets_present(mapping):
    targets = {t["target"] for t in mapping["targets"]["series"]}
    assert {"headline_cpi_mom", "core_cpi_mom", "ppi_final_demand_mom", "core_pce_mom"} <= targets
