# PCE wedge decomposition — where Instrument A's error actually comes from

**Measurement, not modeling.** Nothing here is fitted to the 2.4.4U errors (explicit DO-NOT); no
mapping was changed this session; frozen configs and both live ledger rows are untouched. Window
**2023-01 → 2026-05, n=40** months, Instrument A (full core) at its CPI-day call.

## Reporting conventions (both, never blended)

The print is published to **one decimal place (0.1 pp = 10 bp)**. All figures below are given in bp;
the pp/increment view is stated alongside. **1 pp = 100 bp.**

| Instrument A total error | value |
|---|--:|
| MAE, bp | **7.97 bp** |
| MAE, pp | **0.0797 pp** |
| MAE as a share of one published 0.1pp increment | **0.80×** |
| months within half an increment (\|err\| < 5 bp) | 40% |
| months within one increment (\|err\| < 10 bp) | 68% |
| months ≥ two increments (\|err\| ≥ 20 bp) | 5% |

The rounded-print hit-rates are a **distinct statistic** from the MAE and are never averaged with it.

## The three numbers (signed additive identity)

`total = mapping(non-residue) + residue + weight-vintage + remainder`, holding month by month.

| part | mean signed | mean \|.\| | gross Σ\|component\| | variance share |
|---|--:|--:|--:|--:|
| **total error** | **+0.36 bp** | **7.97 bp** | — | 100% |
| **(2a) mapping, non-residue** | −0.17 | **7.56** | **23.77** | **82.2%** |
| (2b) residue lines *(separate, never blended)* | −3.72 | 4.83 | 8.00 | −3.3% |
| **(1) weight-vintage** | +0.073 | **0.178** | — | **0.2%** |
| **(3) irreducible remainder** | +4.17 | 6.86 | — | 23.4% |

**Pre-registered expectation CONFIRMED.** Mapping dominates (**82.2%** of monthly error variance);
weight-vintage is negligible (**0.2%**, mean 0.178 bp) — independently consistent with H16's null.
Mapping error is ~**130×** the weight-vintage term. The residue lines carry a **−3.72 bp signed**
tilt (the frozen freeze-at-zero specs under-print in this window) but *reduce* total variance slightly.

## The headline finding: the floor is offsetting, not small

**Gross component error is ~4.0× the net error** — 31.77 bp of per-component error per month
(23.77 non-residue + 8.00 residue) collapses to a **7.97 bp** net miss.

The bridge is therefore **not** accurate because each component tracks well. It is accurate because
**large per-component errors substantially cancel.** Consequences, stated plainly:

- The ~7–8 bp floor contains an element of **offsetting luck**. A month in which component errors
  *align* is materially worse — consistent with the observed **max 24.5 bp**.
- Fixing any *single* component in the league table below will move the net error **less** than its
  gross contribution suggests, and could move it in **either direction** (it may be currently
  cancelling another error).
- This is the sharper replacement for "~7 bp structural floor": **the floor is a cancellation
  equilibrium, not a precision achievement.**

## League table — mean \|mapping error × weight\| per component (non-residue)

Ranked by gross magnitude, which is the correct ranking metric for a priority list. **The top of this
table IS the priority list for any future mapping audit.**

| # | component | gross bp | mean signed | n |
|---|---|--:|--:|--:|
| 1 | air_transportation | 3.66 | -0.43 | 40 |
| 2 | recreational_goods_vehicles | 2.70 | -0.03 | 39 |
| 3 | portfolio_management_investment_advice | 2.60 | -0.05 | 40 |
| 4 | hospital_services | 1.79 | -0.21 | 40 |
| 5 | motor_vehicle_services | 1.37 | +0.67 | 39 |
| 6 | professional_other_services | 1.30 | -0.09 | 39 |
| 7 | recreation_services | 1.27 | +0.03 | 39 |
| 8 | food_services_accommodations | 1.21 | +0.02 | 39 |
| 9 | furnishings_durable_household_equipment | 0.93 | -0.02 | 39 |
| 10 | other_durable_goods | 0.89 | +0.40 | 39 |
| 11 | household_supplies | 0.85 | +0.21 | 39 |
| 12 | used_motor_vehicles | 0.63 | +0.07 | 40 |
| 13 | health_insurance_margin | 0.62 | -0.60 | 40 |
| 14 | personal_care_services | 0.56 | -0.13 | 39 |
| 15 | physician_outpatient_services | 0.45 | -0.03 | 40 |
| 16 | nursing_homes | 0.42 | -0.07 | 40 |
| 17 | pharmaceutical_other_medical_products | 0.42 | +0.04 | 39 |
| 18 | clothing_footwear | 0.40 | +0.05 | 39 |
| 19 | life_insurance | 0.34 | -0.34 | 40 |
| 20 | personal_care_products | 0.31 | -0.05 | 39 |
| 21 | communication | 0.30 | +0.21 | 39 |
| 22 | education_services | 0.21 | +0.14 | 39 |
| 23 | dental_services | 0.20 | +0.01 | 39 |
| 24 | home_health_care | 0.20 | -0.01 | 40 |
| 25 | housing_oer | 0.19 | +0.02 | 39 |
| 26 | other_transportation_services | 0.13 | +0.03 | 39 |
| 27 | new_motor_vehicles | 0.11 | +0.01 | 40 |
| 28 | housing_tenant_rent | 0.05 | +0.00 | 39 |
| 29 | household_utilities_water_waste | 0.00 | -0.00 | 39 |
| 30 | tobacco | 0.00 | +0.00 | 39 |
| 31 | group_housing | 0.00 | +0.00 | 39 |

**Residue lines (reported separately, never blended into the trackable total):**

| component | gross bp | mean signed |
|---|--:|--:|
| financial_service_charges_fees | 4.35 | — |
| npish_final_consumption | 2.09 | — |
| financial_services_without_payment | 1.67 | — |

## The worst 5 non-residue components — incomplete (fixable) or concept-divergent (floor)?

All citations from **BEA NIPA Handbook ch.5, Tables 5.A (goods) / 5.B (services)**, retrieved
2026-07-25 from `bea.gov/resources/methodologies/nipa-handbook/pdf/chapter-05.pdf` (69 pp). Quoted
strings are verbatim from that chapter.

**1. `air_transportation` — 3.66 bp — CONCEPT-DIVERGENT (floor).** Table 5.B specifies *"PPI for
domestic scheduled passenger air transportation"*; our bridge uses `PCU481111481111`, which **is**
that series. The mapping is **verified correct** (H9a reached the same conclusion, corr 0.70). So the
single largest gross contributor is **not a mapping bug** — it is the commodity-flow derivation: BEA
deflates a current-dollar estimate built from EC/SAS receipts and BTS revenue data, so its monthly
price path differs from the raw PPI even when the deflator is identical. **Not fixable by remapping.**

**2. `recreational_goods_vehicles` — 2.70 bp — PARTLY INCOMPLETE (fixable in part).** Table 5.A
deflates this line with a **nine-series fixed-weighted set**: *"CPI for televisions, CPI for other
video equipment, CPI for audio equipment, CPI for recorded music and music subscriptions, CPI for
video discs and other media, CPI for photographic equipment, CPI for personal computers and
peripheral equipment, CPI for computer software and accessories, and CPI for telephone hardware,
calculators, and other consumer information items."* Our bridge uses **five CPI aggregates**
(`SERA, SERC, SERE, SEEE01, SEEE02`). Two gaps: the **telephone-hardware/calculators leg is absent**,
and we use CPI *aggregates* (CPI-weighted) where BEA uses *fixed* weights over detail. The first is
an H9a-style fixable omission; the second is a weight-scheme divergence that remains a floor.

**3. `portfolio_management_investment_advice` — 2.60 bp — INCOMPLETE (fixable).** Table 5.B:
*"Fixed-weighted average of PPI for Portfolio management **and PPI for investment advice**."* Our
bridge uses the single successor series `PCU5239205239202` (portfolio management only) — the
**investment-advice leg is missing**. Already documented by R1/H9a; this decomposition now **prices
it at 2.60 bp gross**, making it the highest-value verified-incomplete mapping in the table.

**4. `hospital_services` — 1.79 bp — CONCEPT-DIVERGENT (floor) + a stale note to correct.**
Table 5.B specifies *"PPI for hospitals"*; our bridge uses `PCU622110622110`, which **matches**. The
residual is concept-divergent (BEA's hospital PCE is commodity-flow-derived and all-payer-scoped
against an ECI-based input-cost treatment for some sub-lines). **Correction flagged:** our mapping's
`scope_adjustment_note` claims *"BEA blends with CPI hospital for out-of-pocket share"* — the string
**"out-of-pocket" does not appear anywhere in ch.5**, and 5.B lists only "PPI for hospitals". That
legacy note is **unverified and should be corrected or cited**; it is not evidence of a fixable gap.

**5. `motor_vehicle_services` — 1.37 bp — MISASSIGNED (fixable).** Our bridge bundles
`SETD + SETE + SETF`, i.e. it includes **CPI motor-vehicle insurance (SETE)**. But BEA's `DMVS` covers
maintenance/repair/lease/rental/parking, while insurance sits in a **separate NIPA line** — *"Net
motor vehicle and other transportation insurance"*, deflated by *"PPI for private passenger auto
insurance"* (5.B), on a **net-premium** (premiums-less-losses) concept rather than CPI's gross
premium. R1 already recorded this scope gap; the decomposition prices it at **1.37 bp gross**. Fixable
by moving SETE out of this component — but note the concept difference (net vs gross premium) means
the *deflator* substitution is itself only partly available to us.

## What this justifies (no remapping performed this session)

Three **verified-incomplete** mappings are now priced: portfolio's missing investment-advice leg
(2.60 bp), recreational goods' missing telephone-hardware leg (2.70 bp, partial), and motor-vehicle
insurance's misassignment (1.37 bp). Together they are the only candidates in the table with a
documented, citable fix.

**A pre-registered H18 would be justified in scope** — but the offset finding above sets its
expectation honestly: because gross error is 4× net, correcting these three could plausibly leave the
net MAE **unchanged or slightly worse**. Any H18 must therefore pre-register *both* directions as
acceptable outcomes, and must be judged on **per-component tracking error against 2.4.4U** (the thing
actually being fixed) rather than on aggregate MAE alone. **No H18 is opened here.**
