# License note — nadac (National Average Drug Acquisition Cost)

Reviewed: 2026-07-19.

**Source.** CMS / Medicaid — NADAC (National Average Drug Acquisition Cost), per-NDC
retail pharmacy acquisition cost. Yearly full-history CSVs from
`https://download.medicaid.gov/data/nadac-national-average-drug-acquisition-cost-12-31-{YEAR}.csv`
(dataset index: data.medicaid.gov). Public data, one file per year.

**Terms.** U.S. Government work, public domain (CMS open data). We fetch each yearly
CSV once per run with an identified User-Agent, well under human-browsing intensity.
No auth wall, no CAPTCHA. Attribution to CMS/Medicaid retained in provenance.

**Vintage status.** `unrevised` (verified against CMS documentation): NADAC publishes a
weekly reference file; a drug's NADAC for a given effective_date holds until a survey
changes it going forward — historical effective-dated values are not retroactively
restated. (If a future audit finds restatement, reclassify to revised_latest_only.)

**Index construction — PLACEHOLDER, marked for 3A upgrade.** Per-NDC weekly prices are
aggregated to a monthly mean per NDC, then a **matched-model geometric-mean-of-relatives**
index is chained across consecutive months (NDCs present in both months only — mirrors
Jevons-within-stratum conceptually). This is a deterministic PLACEHOLDER: Session 3A
replaces it with the proper population/spend-weighted matched-model index. Basket rule
in spec.yaml.
