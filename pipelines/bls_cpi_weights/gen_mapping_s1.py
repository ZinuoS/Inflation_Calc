"""Generate mapping/mapping.yaml (Session 1, Task 2).

One-off generator: parses the Dec-2025 BLS relative-importance pull in data/raw/,
joins item codes + SA availability from the BLS cu.* reference files, overlays
curated formula exceptions and the research-plan alt-data source table, and
appends hand-written PPI and PCE-bridge sections. Regeneration moves into the
bls_cpi_weights naru pipeline in Session 2.
"""
import re
import pandas as pd
import yaml

RAW = "data/raw/bls_cpi_weights/2026-07-18"
ASOF = "2025-12"

# ---------- parse RI hierarchy ----------
df = pd.read_excel(f"{RAW}/relative_importance_2025.xlsx", sheet_name="Table 1", header=None)
df.columns = ["indent", "item", "cpi_u", "cpi_w"]
panel = df.iloc[9:313].copy()
panel = panel[pd.notna(panel["indent"]) & pd.notna(panel["item"])]
panel["indent"] = panel["indent"].astype(int)
panel["name"] = panel["item"].astype(str).str.strip()
panel = panel[panel["name"] != "All items"]

def norm(s):
    s = re.sub(r"\(\d+\)", "", str(s)).replace("’", "'")
    s = s.replace(",", "").replace(" and ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()

ALIASES = {  # RI-table wording -> cu.item wording (BLS renamed these)
    "Housing at school, excluding board": "Lodging while at school",
    "Technical and business school tuition and fees": "Technical and vocational school tuition and fixed fees",
}

items = pd.read_csv(f"{RAW}/cu_item.txt", sep="\t")
items.columns = [c.strip() for c in items.columns]
name2code = {norm(n): c.strip() for n, c in zip(items["item_name"], items["item_code"])}

series = pd.read_csv(f"{RAW}/cu_series.txt", sep="\t", dtype=str)
series.columns = [c.strip() for c in series.columns]
series = series[series["area_code"].str.strip() == "0000"]
sa_codes = set(series[series["seasonal"].str.strip() == "S"]["item_code"].str.strip())
nsa_codes = set(series[series["seasonal"].str.strip() == "U"]["item_code"].str.strip())

rows = panel.to_dict("records")
for i, r in enumerate(rows):
    lookup = ALIASES.get(r["name"], r["name"])
    r["item_code"] = name2code.get(norm(lookup))
    r["is_leaf"] = not (i + 1 < len(rows) and rows[i + 1]["indent"] > r["indent"])

# parent chain from indent stack
stack = []
for r in rows:
    while stack and stack[-1]["indent"] >= r["indent"]:
        stack.pop()
    r["parent_code"] = stack[-1]["item_code"] if stack else "SA0"
    r["parent_name"] = stack[-1]["name"] if stack else "All items"
    r["ancestors"] = tuple(s["name"] for s in stack)
    stack.append(r)

# BLS Table-1 printed indents mislead in two places; repair to official structure.
# (1) Alcoholic beverages (SAF116) is a sibling of Food under Food and beverages.
# (2) "Information technology, hardware and services" is printed at indent 3 but is
#     a child of Information and information processing (1.466 + 1.714 = 3.181).
PARENT_FIXES = {
    "Alcoholic beverages": "Food and beverages",
    "Information technology, hardware and services": "Information and information processing",
}
code_by_name = {r["name"]: r["item_code"] for r in rows}
for r in rows:
    if r["name"] in PARENT_FIXES:
        r["parent_code"] = code_by_name[PARENT_FIXES[r["name"]]]
        r["parent_name"] = PARENT_FIXES[r["name"]]

# ---------- curated overlays ----------
# Arithmetic (non-geomean) strata, BLS Handbook of Methods ch. 17 ("geometric
# mean formula used for all item strata except shelter and selected
# utilities/government-charge strata"). Verify full list in Session 2.
ARITH_PREFIXES = ("SEHA", "SEHB01", "SEHC", "SEHF", "SEHG01", "SEHG02", "SEEC01")

def formula_for(code, name):
    if not code:  # unsampled/unpublished stratum -- no index to price
        return "none_unsampled"
    if any(code.startswith(p) for p in ARITH_PREFIXES):
        return "arithmetic"
    return "jevons"

# alt-data table (research plan §1.4, resolved per D1; sources from §2 and §5.2).
# key: regex on stratum name (applied to leaves). plan_ref: 2B-A/2B-B = published
# pipeline (Session 2B group), S5-n = forward collector (Session 5 priority n).
ALT = [
    (r"^Gasoline \(all types\)$", dict(alt_source="eia_weekly_gasoline", alt_status="build", plan_ref="2B-A",
        proxy_source="eia_weekly_retail_gasoline", proxy_history_start=1993, license_status="public_domain", confidence="high")),
    (r"^Fuel oil$", dict(alt_source="eia_heating_oil", alt_status="build", plan_ref="2B-A",
        proxy_source="eia_no2_heating_oil", proxy_history_start=1990, license_status="public_domain", confidence="high")),
    (r"^Utility \(piped\) gas service$", dict(alt_source=None, alt_status="none", plan_ref=None,
        proxy_source="henry_hub_spot", proxy_history_start=1997, license_status="public_domain", confidence="low",
        note="spot leads retail by 1-2 months; pass-through unstable")),
    (r"^(Beef and veal|Pork|Other meats|Poultry|Fish and seafood|Eggs|Meats, poultry, and fish)$",
        dict(alt_source="usda_ams_retail", alt_status="build", plan_ref="2B-A",
        proxy_source="usda_ams_retail_reports", proxy_history_start=2004, license_status="public_domain", confidence="medium")),
    (r"^(Milk|Cheese and related products|Ice cream and related products|Other dairy and related products)$",
        dict(alt_source="usda_ams_retail", alt_status="build", plan_ref="2B-A",
        proxy_source="usda_ams_retail_reports", proxy_history_start=2004, license_status="public_domain", confidence="medium")),
    (r"^(Apples|Bananas|Citrus fruits|Other fresh fruits|Potatoes|Lettuce|Tomatoes|Other fresh vegetables|Fresh fruits|Fresh vegetables)$",
        dict(alt_source="usda_ams_retail", alt_status="build", plan_ref="2B-A",
        proxy_source="usda_ams_retail_reports", proxy_history_start=2004, license_status="public_domain", confidence="medium")),
    (r"^(Full service meals and snacks|Limited service meals and snacks)$",
        dict(alt_source="chain_menu_prices", alt_status="build", plan_ref="S5-1",
        proxy_source=None, proxy_history_start=None, license_status="per_chain_tos_review", confidence="medium",
        note="forward-only accumulator; delivery markup spread (S5-6) also maps here; OpenTable/wage trackers monitor-only")),
    (r"^New vehicles$", dict(alt_source="cox_atp", alt_status="build", plan_ref="2B-B",
        proxy_source="cox_atp_press_archive", proxy_history_start=2012, license_status="published_headline", confidence="medium")),
    (r"^Used cars and trucks$", dict(alt_source="manheim_headlines", alt_status="build", plan_ref="2B-B",
        proxy_source="manheim_uvvi_published", proxy_history_start=1997, license_status="published_headline", confidence="high",
        note="mid-month vs full-month kept distinct (H1)")),
    (r"^Airline fares$", dict(alt_source="google_flights_basket", alt_status="build", plan_ref="S5-2",
        proxy_source="tsa_throughput", proxy_history_start=2019, license_status="public_domain", confidence="low",
        note="TSA is demand not price; scraped basket is the real layer")),
    (r"^Rent of primary residence$", dict(alt_source=None, alt_status="none", plan_ref="2B-A",
        proxy_source="zori", proxy_history_start=2015, license_status="published_download", confidence="medium",
        note="also apartment_list (2017), zumper, bls_new_tenant_rent (2005, quarterly); H2: new-lease indices lead ~1y, expected NOT to help next print")),
    (r"^Owners' equivalent rent of primary residence$", dict(alt_source=None, alt_status="none", plan_ref="2B-A",
        proxy_source="zori", proxy_history_start=2015, license_status="published_download", confidence="medium",
        note="scope: OER derived from rent sample; same H2 caveat")),
    (r"^Other lodging away from home", dict(alt_source="str_occupancy_adr", alt_status="vendor_only", plan_ref=None,
        proxy_source=None, proxy_history_start=None, license_status="restricted", confidence="low",
        note="[SCRAPE-RESTRICTED] per D1: excluded from core; no public backup -> carry consensus")),
    (r"^(Men's|Women's|Boys'|Girls'|Footwear|Infants' and toddlers'|Jewelry|Watches)",
        dict(alt_source="adobe_dpi", alt_status="build", plan_ref="2B-B",
        proxy_source="adobe_dpi_press_archive", proxy_history_start=2014, license_status="published_headline", confidence="medium")),
    (r"^Prescription drugs$", dict(alt_source="drug_basket_goodrx_costplus_nadac", alt_status="build", plan_ref="S5-3",
        proxy_source="nadac", proxy_history_start=2013, license_status="public_domain", confidence="high")),
    (r"^Hospital services$", dict(alt_source="cms_hospital_transparency", alt_status="build", plan_ref="S5-4",
        proxy_source="ppi_hospitals_PCU622110622110", proxy_history_start=1993, license_status="public_domain", confidence="medium")),
    (r"^Physicians' services$", dict(alt_source=None, alt_status="none", plan_ref=None,
        proxy_source="ppi_physicians_PCU621111621111", proxy_history_start=1994, license_status="public_domain", confidence="medium")),
    (r"^Health insurance$", dict(alt_source=None, alt_status="none", plan_ref=None,
        proxy_source=None, proxy_history_start=None, license_status=None, confidence="high",
        note="unmodeled by design: BLS retained-earnings method, annual rebasing -> carry consensus")),
    (r"^Motor vehicle insurance$", dict(alt_source=None, alt_status="none", plan_ref=None,
        proxy_source="ppi_pc_insurance_PCU524126524126", proxy_history_start=1998, license_status="public_domain", confidence="low",
        note="premium-rate filings differ from CPI quality adjustment; monitor only")),
    (r"^Cable, satellite, and live streaming television service$",
        dict(alt_source="streaming_tracker", alt_status="build", plan_ref="S5-5",
        proxy_source=None, proxy_history_start=None, license_status="per_site_tos_review", confidence="medium")),
    (r"^(Televisions|Computers, peripherals, and smart home assistant devices|Audio equipment|Video and audio products)",
        dict(alt_source="adobe_dpi", alt_status="build", plan_ref="2B-B",
        proxy_source="adobe_dpi_press_archive", proxy_history_start=2014, license_status="published_headline", confidence="medium")),
    (r"^(Furniture and bedding|Major appliances|Other appliances)", dict(alt_source="adobe_dpi", alt_status="build", plan_ref="2B-B",
        proxy_source="adobe_dpi_press_archive", proxy_history_start=2014, license_status="published_headline", confidence="low")),
    (r"^Intracity transportation$", dict(alt_source=None, alt_status="none", plan_ref=None,
        proxy_source="nyc_tlc_trip_data", proxy_history_start=2009, license_status="public_domain", confidence="low",
        note="NYC-only coverage of a national stratum")),
    (r"^Electricity$", dict(alt_source=None, alt_status="none", plan_ref=None,
        proxy_source="eia_electric_power_monthly", proxy_history_start=2001, license_status="public_domain", confidence="low",
        note="published with ~2-month lag; trajectory monitor, weak next-print value")),
    (r"^Dental services$", dict(alt_source=None, alt_status="none", plan_ref=None,
        proxy_source="ppi_dentists_PCU621210621210", proxy_history_start=1994, license_status="public_domain", confidence="low")),
    (r"^Motor vehicle maintenance and servicing$", dict(alt_source=None, alt_status="none", plan_ref=None,
        proxy_source="ppi_auto_repair_id_TBD", proxy_history_start=None, license_status="public_domain", confidence="low",
        note="PPI auto repair industry series exists; exact id verified in Session 2B")),
    (r"^Pet services including veterinary$", dict(alt_source=None, alt_status="none", plan_ref=None,
        proxy_source="ppi_veterinary_id_TBD", proxy_history_start=None, license_status="public_domain", confidence="low",
        note="PPI veterinary services series exists; exact id verified in Session 2B")),
]

GROCERY_FALLBACK = dict(alt_source="adobe_dpi", alt_status="build", plan_ref="2B-B",
    proxy_source="adobe_dpi_groceries", proxy_history_start=2019, license_status="published_headline",
    confidence="low", note="Adobe online-grocery category; online/offline mix differs from CPI outlet frame")

def alt_for(name, ancestors=()):
    for pat, entry in ALT:
        if re.search(pat, name):
            return dict(entry)
    if "Food at home" in ancestors and "unsampled" not in name.lower():
        return dict(GROCERY_FALLBACK)
    return dict(alt_source=None, alt_status="none", plan_ref=None, proxy_source=None,
                proxy_history_start=None, license_status=None, confidence=None)

# ---------- assemble CPI section ----------
cpi_items = []
for r in rows:
    code = r["item_code"]
    published = code is not None
    sa = bool(code and code in sa_codes)
    d = {
        "name": r["name"],
        "item_code": code,
        "parent_code": r["parent_code"],
        "indent": r["indent"],
        "weight_cpi_u": round(float(r["cpi_u"]), 3),
        "is_stratum": bool(r["is_leaf"]),
        "published": published,
        "series_id": (f"CUSR0000{code}" if sa else (f"CUUR0000{code}" if published else None)),
        "sa_flag": sa,
    }
    if r["is_leaf"]:
        d["lower_level_formula"] = formula_for(code, r["name"])
        a = alt_for(r["name"], r.get("ancestors", ()))
        note = a.pop("note", None)
        d["alt"] = a
        if note:
            d["alt"]["note"] = note
    cpi_items.append(d)

leaves = [d for d in cpi_items if d["is_stratum"]]

special_aggregates = [
    {"name": "All items", "item_code": "SA0", "series_id": "CUSR0000SA0", "role": "headline_cpi_target"},
    {"name": "All items less food and energy", "item_code": "SA0L1E", "series_id": "CUSR0000SA0L1E", "role": "core_cpi_target"},
    {"name": "Energy", "item_code": "SA0E", "series_id": "CUSR0000SA0E", "role": "energy_aggregate"},
    {"name": "Food", "item_code": "SAF1", "series_id": "CUSR0000SAF1", "role": "food_aggregate"},
    {"name": "Commodities less food and energy commodities", "item_code": "SACL1E", "series_id": "CUSR0000SACL1E",
     "role": "core_goods", "monitor_sources": ["freightos_fbx (2016)", "drewry_wci (2011)", "import_price_indexes"],
     "note": "H4: freight/pipeline layer leads 1-2 quarters, trajectory value only"},
    {"name": "Services less energy services", "item_code": "SASLE", "series_id": "CUSR0000SASLE",
     "role": "core_services", "monitor_sources": ["indeed_wage_tracker (2019)", "atlanta_fed_wage_tracker (1997)"],
     "note": "wage trackers are cost-pressure monitors, never next-print features"},
]

# ---------- PPI section (hand-curated) ----------
ppi = {
    "note": "Final demand structure; ids are BLS PPI series. WPS* = SA, WPU* = NSA. "
            "pce_feeders are the industry PPIs BEA uses (or that best approximate what BEA uses) "
            "for PCE deflation; confidence low where BEA's exact source detail is not public.",
    "final_demand": [
        {"name": "Final demand", "series_id_nsa": "WPUFD4", "series_id_sa": "WPSFD4", "role": "ppi_headline_target"},
        {"name": "Final demand goods", "series_id_nsa": "WPUFD41", "series_id_sa": "WPSFD41"},
        {"name": "Final demand foods", "series_id_nsa": "WPUFD411", "series_id_sa": "WPSFD411"},
        {"name": "Final demand energy", "series_id_nsa": "WPUFD412", "series_id_sa": "WPSFD412"},
        {"name": "Final demand goods less foods and energy", "series_id_nsa": "WPUFD413", "series_id_sa": "WPSFD413"},
        {"name": "Final demand services", "series_id_nsa": "WPUFD42", "series_id_sa": "WPSFD42"},
        {"name": "Final demand trade services", "series_id_nsa": "WPUFD421", "series_id_sa": "WPSFD421"},
        {"name": "Final demand transportation and warehousing services", "series_id_nsa": "WPUFD422", "series_id_sa": "WPSFD422"},
        {"name": "Final demand services less trade, transportation, and warehousing", "series_id_nsa": "WPUFD423", "series_id_sa": "WPSFD423"},
        {"name": "Final demand construction", "series_id_nsa": "WPUFD43", "series_id_sa": "WPSFD43"},
        {"name": "Final demand less foods and energy", "series_id_nsa": "WPUFD49104", "series_id_sa": "WPSFD49104", "role": "ppi_core"},
        {"name": "Final demand less foods, energy, and trade services", "series_id_nsa": "WPUFD49116", "series_id_sa": "WPSFD49116"},
    ],
    "pce_feeders": [
        {"pce_component": "hospital_services", "series_id": "PCU622110622110",
         "name": "PPI general medical and surgical hospitals", "confidence": "medium"},
        {"pce_component": "physician_services", "series_id": "PCU621111621111",
         "name": "PPI offices of physicians", "confidence": "medium"},
        {"pce_component": "home_health_care", "series_id": "PCU621610621610",
         "name": "PPI home health care services", "confidence": "medium"},
        {"pce_component": "nursing_home_services", "series_id": "PCU623110623110",
         "name": "PPI nursing care facilities", "confidence": "medium"},
        {"pce_component": "air_transportation", "series_id": "PCU481111481111",
         "name": "PPI scheduled passenger air transportation", "confidence": "medium"},
        {"pce_component": "portfolio_management", "series_id": "PCU523920523920",
         "name": "PPI portfolio management and investment advice", "confidence": "medium"},
        {"pce_component": "property_casualty_insurance", "series_id": "PCU524126524126",
         "name": "PPI direct property and casualty insurers", "confidence": "low",
         "note": "BEA nets expected losses; premium PPI is an approximation"},
    ],
}

# ---------- PCE bridge (hand-curated; BEA 'PCE Sources and Methods' is the doctrine) ----------
def b(component, source_type, source_series, scope, weight_source="bea_pce_detail_pipeline_nominal_shares",
      in_core=True, confidence="medium"):
    return {"component": component, "source_type": source_type, "source_series": source_series,
            "scope_adjustment_note": scope, "weight_source": weight_source,
            "in_core": in_core, "confidence": confidence}

pce_bridge = {
    "note": "Core-PCE assembly table (plan §1.3): after CPI+PPI print, PCE is arithmetic. "
            "source_series lists reference cpi item_codes (S*) and PPI series (PCU*) defined above; "
            "bea_imputed rows have source_series null and an approximation note. confidence: low rows "
            "are best-documented approximations, NOT verified BEA practice — review list in "
            "docs/checkpoint_log_s1.md. Core excludes food-off-premises and energy goods+services.",
    "components": [
        # -- durables
        b("new_motor_vehicles", "cpi_relative", ["SETA01"], "fleet/consumer split differs; BEA quality-adjusts with own detail"),
        b("used_motor_vehicles", "cpi_relative", ["SETA02"], "PCE prices dealer margin, not gross transaction; margin treatment differs", confidence="low"),
        b("furnishings_durable_household_equipment", "cpi_relative", ["SEHJ", "SEHK", "SEHL"], "rural + institutional population included in PCE"),
        b("recreational_goods_vehicles", "cpi_relative", ["SERA", "SERC", "SERE", "SEEE01", "SEEE02"], "computers/software partly PPI-deflated by BEA", confidence="low"),
        b("other_durable_goods", "cpi_relative", ["SEMG", "SEAG"], "medical equipment + jewelry/watches; scope differences minor"),
        # -- nondurables (core part)
        b("clothing_footwear", "cpi_relative", ["SAA"], "NPISH clothing included"),
        b("pharmaceutical_other_medical_products", "cpi_relative", ["SEMF01", "SEMF02"], "PCE includes employer/government-paid share; CPI is out-of-pocket only", confidence="low"),
        b("household_supplies", "cpi_relative", ["SEHN"], "minor scope"),
        b("personal_care_products", "cpi_relative", ["SEGB"], "minor scope"),
        b("tobacco", "cpi_relative", ["SEGA"], "minor scope"),
        b("food_beverages_off_premises", "cpi_relative", ["SAF11", "SEFW"], "EXCLUDED from core (BEA food = off-premises food + off-premises alcohol)", in_core=False),
        b("gasoline_other_energy_goods", "cpi_relative", ["SETB01", "SEHE"], "EXCLUDED from core", in_core=False),
        # -- services
        b("housing_tenant_rent", "cpi_relative", ["SEHA"], "PCE includes rural + farm dwellings fully", confidence="high"),
        b("housing_oer", "cpi_relative", ["SEHC"], "same rent-sample derivation; PCE space-rent concept", confidence="high"),
        b("group_housing", "bea_imputed", None, "dormitories, group homes — BEA input-cost imputation", confidence="low"),
        b("household_utilities_water_waste", "cpi_relative", ["SEHG01", "SEHG02"], "water/sewer/trash IS in core (not energy)"),
        b("electricity_natural_gas", "cpi_relative", ["SEHF01", "SEHF02"], "EXCLUDED from core (energy services)", in_core=False),
        b("physician_outpatient_services", "ppi_relative", ["PCU621111621111"], "PCE covers all-payer (Medicare/Medicaid/employer), CPI only out-of-pocket — this is why PPI not CPI"),
        b("dental_services", "cpi_relative", ["SEMC02"], "partial all-payer adjustment by BEA", confidence="low"),
        b("home_health_care", "ppi_relative", ["PCU621610621610"], "all-payer scope"),
        b("hospital_services", "ppi_relative", ["PCU622110622110"], "all-payer scope; BEA blends with CPI hospital for out-of-pocket share"),
        b("nursing_homes", "ppi_relative", ["PCU623110623110"], "all-payer scope"),
        b("health_insurance_margin", "bea_imputed", None, "BEA prices insurance as margin (premiums less benefits) — no CPI analogue", confidence="low"),
        b("motor_vehicle_services", "cpi_relative", ["SETD", "SETE", "SETF"], "insurance component uses BEA net-premium concept vs CPI gross premium", confidence="low"),
        b("air_transportation", "ppi_relative", ["PCU481111481111"], "PPI covers all fare classes incl. business; CPI basket differs"),
        b("other_transportation_services", "cpi_relative", ["SETG02", "SETG03"], "intercity + intracity transit", confidence="low"),
        b("recreation_services", "cpi_relative", ["SERF", "SERA02", "SERB02", "SERD02"], "NPISH admissions included; BEA adds gambling/package tours from own detail", confidence="low"),
        b("food_services_accommodations", "cpi_relative", ["SEFV", "SEHB"], "food services ARE in core (only off-premises food excluded)"),
        b("financial_service_charges_fees", "cpi_relative", ["SEGD05"], "CPI financial services stratum covers bank/checking fees; BEA mixes in PPI deposit-service charges", confidence="low"),
        b("portfolio_management_investment_advice", "ppi_relative", ["PCU523920523920"], "known BEA source; strongly market-linked"),
        b("financial_services_without_payment", "bea_imputed", None,
          "imputed bank services: BEA user-cost method. Approximation: deposit/loan balances x rate spreads; equity-linked fees via S&P500 path", confidence="low"),
        b("life_insurance", "bea_imputed", None, "expected-benefit margin method", confidence="low"),
        b("communication", "cpi_relative", ["SEED", "SEEE03", "SEEC"], "wireless quality adjustment differs; postal included in BEA communication"),
        b("education_services", "cpi_relative", ["SEEB"], "PCE nets scholarships; NPISH education imputed from input costs", confidence="low"),
        b("professional_other_services", "cpi_relative", ["SEGD01", "SEGD02", "SEGD03", "SEGD04"], "legal/funeral/laundry/apparel services", confidence="low"),
        b("personal_care_services", "cpi_relative", ["SEGC"], "minor scope"),
        b("npish_final_consumption", "bea_imputed", None, "input-cost based, no market price; carry trend", confidence="low"),
    ],
}

# hard validation: every referenced code must resolve
_cpi_codes = {r["item_code"] for r in rows if r["item_code"]} | {"SA0"}
_ppi_ids = {f["series_id"] for f in ppi["pce_feeders"]}
_unknown = []
for comp in pce_bridge["components"]:
    for tok in (comp["source_series"] or []):
        if tok.startswith("PCU"):
            if tok not in _ppi_ids: _unknown.append((comp["component"], tok, "not in ppi.pce_feeders"))
        elif tok not in _cpi_codes:
            _unknown.append((comp["component"], tok, "not a cpi item_code"))
if _unknown:
    raise SystemExit(f"orphan source_series tokens: {_unknown}")

targets = {
    "note": "D2 targets: MoM surprise vs consensus, unrounded where available; first-release (ALFRED) values.",
    "series": [
        {"target": "headline_cpi_mom", "series_id": "CUSR0000SA0", "alfred_id": "CPIAUCSL"},
        {"target": "core_cpi_mom", "series_id": "CUSR0000SA0L1E", "alfred_id": "CPILFESL"},
        {"target": "ppi_final_demand_mom", "series_id": "WPSFD4", "alfred_id": "PPIFIS"},
        {"target": "core_pce_mom", "series_id": None, "alfred_id": "PCEPILFE",
         "note": "unrounded two-decimal from BEA underlying detail where available"},
        {"target": "headline_pce_mom", "series_id": None, "alfred_id": "PCEPI"},
    ],
}

mapping = {
    "meta": {
        "generated": "2026-07-18",
        "session": "S1/Task2",
        "weight_source_file": f"{RAW}/relative_importance_2025.xlsx (sha256 6e7baa9b...55, CPI-U relative importance, Dec {ASOF[:4]})",
        "weight_asof": ASOF,
        "regeneration": "bls_cpi_weights naru pipeline (Session 2) replaces this hand pull",
        "formula_exceptions_citation": "BLS Handbook of Methods ch.17 — arithmetic-mean strata = shelter + selected utilities/gov-charges; VERIFY full list in Session 2",
        "alt_table_provenance": "research plan §1.4/§2/§5.2 (docs/research_plan.md, v0.1); standalone 20-row draft table was not available — reconstructed, rows cite plan_ref",
    },
    "targets": targets,
    "cpi": {
        "weight_basis": "cpi_u_relative_importance",
        "asof": ASOF,
        "special_aggregates": special_aggregates,
        "items": cpi_items,
    },
    "ppi": ppi,
    "pce_bridge": pce_bridge,
}

with open("mapping/mapping.yaml", "w") as f:
    f.write("# mapping.yaml — generated by Session-1 Task-2 generator (see meta.regeneration)\n"
            "# Edit alt/bridge rows by hand; CPI hierarchy+weights regenerate from raw pull.\n")
    yaml.safe_dump(mapping, f, sort_keys=False, allow_unicode=True, width=110)

# ---------- coverage stats (Checkpoint 2) ----------
tot = sum(l["weight_cpi_u"] for l in leaves)
w_proxy = sum(l["weight_cpi_u"] for l in leaves if l["alt"]["proxy_source"])
w_scrape = sum(l["weight_cpi_u"] for l in leaves if l["alt"]["plan_ref"] and l["alt"]["plan_ref"].startswith("S5"))
w_pipe2b = sum(l["weight_cpi_u"] for l in leaves if l["alt"]["plan_ref"] and l["alt"]["plan_ref"].startswith("2B"))
w_unmod = sum(l["weight_cpi_u"] for l in leaves if not l["alt"]["proxy_source"] and l["alt"]["alt_status"] in ("none", "vendor_only"))
w_any = sum(l["weight_cpi_u"] for l in leaves if l["alt"]["proxy_source"] or l["alt"]["alt_status"] == "build")
unsampled = [l for l in leaves if not l["published"]]
missing_alt = [l for l in leaves if "alt" not in l]

print(f"strata (leaves): {len(leaves)}, leaf weight sum: {tot:.3f}")
print(f"unsampled/unpublished strata: {len(unsampled)}, weight {sum(l['weight_cpi_u'] for l in unsampled):.3f}")
print(f"(i)   any published proxy:        {w_proxy:6.3f}  ({w_proxy/tot*100:.1f}%)")
print(f"      via 2B published pipelines: {w_pipe2b:6.3f}")
print(f"(ii)  planned scraped layer (S5): {w_scrape:6.3f}  ({w_scrape/tot*100:.1f}%)")
print(f"(any signal: proxy or build):     {w_any:6.3f}  ({w_any/tot*100:.1f}%)")
print(f"(iii) unmodeled/carry-consensus:  {w_unmod:6.3f}  ({w_unmod/tot*100:.1f}%)")
print(f"strata with no alt entry: {len(missing_alt)}")
print(f"sa_flag true: {sum(1 for l in leaves if l['sa_flag'])}/{len(leaves)} strata")
print(f"arithmetic strata: {[l['name'] for l in leaves if l.get('lower_level_formula')=='arithmetic']}")
