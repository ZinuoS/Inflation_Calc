# Inflation Nowcast Research Plan

Component-level CPI / PPI / PCE nowcasting with alt-data layers

Status: DRAFT v0.1 — pre-build. No code until Phase 0 gates clear.

## 0. Governing decisions (GATE 0 — resolve before any code)

**D1 — Project identity: OSS core + firm application layer (two-repo doctrine).**

* Core (personal, open-source, Apache-2.0): methodology replication engine, CPI/PPI→PCE bridge, published-proxy ingestion pipelines, validation harness. Personal hardware, public/permissive data only. Transferability to the firm happens ONLY via OSS adoption — the firm uses the public repo like any dependency. No private handover, ever; intent-to-deliver converts personal work into work product.
* Application layer (firm-side only, does not exist yet): consensus feeds, firm data, positioning logic, live desk use. Built on firm systems with sign-off if and when the desk adopts the core. Ash contributes to this layer only as sanctioned firm work.
* All sources marked [SCRAPE-RESTRICTED] are excluded from the core and replaced by published-proxy backups.

**D1b — Collaboration protocol (analyst).**

* Analyst role: design interlocutor and named early user. NOT a co-author, NOT a code contributor. No commits, no firm data, no desk knowledge into the core repo (their contributions would be arguable Nomura work product and would taint repo IP).
* Any desk-side use of the core routes through the analyst's own management chain.
* Disclosure: brief note to manager re: personal OSS project with a desk colleague as early user, before the collaboration deepens. Cheap insurance; protects both parties and the return-offer position.

**D2 — Success metric (fixed now, before any model exists).**

* Primary: out-of-sample hit rate and MAE on the surprise (print minus Bloomberg/consensus median), not the level, for: core CPI MoM, headline CPI MoM, core PCE MoM, PPI final demand MoM.
* Benchmarks to beat: (i) consensus itself (surprise = 0 forecast), (ii) Cleveland Fed nowcast, (iii) AR(1) on the component.
* A model that does not beat (i) and (ii) OOS is reported as a failure, per ML doctrine. No metric shopping after the fact.

**D3 — Vintage discipline.** All historical targets and macro covariates from ALFRED / point-in-time vintages. First-release values as targets (that is what the market trades), revised values tracked separately. Seasonal factors as-of-date, not current.

## 1. Phase 1 — Target decomposition & mapping (1–2 weeks, no scraping)

Deliverable: `mapping.yaml` — the skeleton everything hangs on.

1.1 Enumerate CPI structure: 8 major groups → expenditure classes → item strata (ELIs). Pull current relative-importance weights (BLS publishes monthly). Record which strata are priced with Jevons (geometric mean, lower level) vs. arithmetic (upper level Laspeyres-type with lagged expenditure weights).

1.2 Enumerate PPI final-demand structure and the specific PPI series that feed PCE components (healthcare, airfares, financial services, insurance).

1.3 Build the CPI/PPI → PCE bridge table: for each PCE component, its source series (CPI relative, PPI relative, or BEA imputation), weight differences (PCE weights from expenditure data, Fisher chain-weighted; CPI weights from consumer survey, biennial-lagged), and scope differences (rural, employer-paid healthcare, NPISH). This table IS the PCE model — after CPI and PPI print, PCE is arithmetic.

1.4 For each item stratum: assign (alt-data source, published-proxy source, historical depth of proxy, expected lead time vs. print, CPI weight). Reuse the 20-row source table already drafted; resolve every [SCRAPE-RESTRICTED] source per D1.

**Gate 1:** mapping.yaml reviewed; weights sum; every stratum has a proxy or an explicit "unmodeled — carry consensus" flag. Target: ≥80% of CPI weight covered by some signal, 100% accounted for.

## 2. Phase 2 — Historical backbone dataset (2–3 weeks)

All backtesting lives here. Sources: FRED/ALFRED, BLS flat files, BEA underlying detail tables, EIA, USDA AMS, Manheim published headlines, Cox ATP, ZORI, Apartment List, Zumper archives, Adobe DPI press-release archive, Freightos/Drewry, Indeed Wage Tracker, Atlanta Fed, NADAC, TSA, OpenTable archive, NYC TLC. Depth target: ≥8 years where available; minimum 5.

2.1 Ingestion as naru-style frozen Pipeline Artifacts: each source → deterministic parser → SQLite, with schema, provenance, retrieval timestamp, license note per source.

2.2 Alignment layer: everything to a monthly grid matching BLS reference periods (CPI pricing occurs throughout month; energy weekly→monthly averaging must match BLS convention; Manheim mid-month vs full-month distinction preserved).

2.3 Release calendar table: exact historical release datetimes for CPI/PPI/PCE/consensus, so every backtest row knows what was knowable at forecast time. This table is the leakage firewall.

**Gate 2:** reconciliation harness passes — each proxy regressed on its official component over full history; report R², stability across 3-year subwindows, and known break points (COVID, 2021–22 inflation, 2025 tariffs). Proxies with unstable sign get flagged, not silently kept.

## 3. Phase 3 — Methodology replication engine (2–3 weeks)

Scope: replicate aggregation, not field sampling. Explicit non-goals: outlet sampling frames, hedonic regressions for apparel/electronics (approximate with BLS published quality-adjustment magnitudes), OER tenant-survey mechanics.

3.1 Lower-level index: Jevons within stratum from any basket of item prices (this is what scraped baskets feed later).

3.2 Upper-level: Laspeyres-type aggregation with BLS relative-importance weights, updated on BLS schedule (as-of-date weights, per D3).

3.3 Seasonal adjustment: X-13ARIMA-SEATS via statsmodels, refit per vintage; verify against BLS published SA factors on 3 test strata (used cars, apparel, airfares). Document residual SA error — it is a real floor on achievable accuracy.

3.4 PCE assembly: implement the Phase-1 bridge table with Fisher chain-weighting; validate by reconstructing historical core PCE MoM (unrounded, two-decimal) from historical CPI/PPI components. Acceptance (two-tier, trade-relevant):

* Tier 1 (accuracy): MAE ≤ 2.0bp on unrounded core PCE MoM over trailing 5 years; stretch 1.5bp ex-COVID months. Note the irreducible floor: BEA uses unpublished source detail, own seasonal factors, and imputations (financial services, insurance) — sub-1bp systematic accuracy is not achievable from public data; a gate demanding it fails for unfixable reasons.
* Tier 2 (rounding-boundary call): correct side of the headline rounding boundary (0.x5 thresholds) in ≥85% of months where the unrounded estimate sits ≥1.5bp from the boundary. Months inside 1.5bp of the boundary are flagged "coin-flip prints" in the report — itself desk-relevant output. This module alone is a usable deliverable (post-CPI-day PCE call).

3.5 PPI mini-model: final demand from freight, commodity spot, ISM/regional-Fed prices-paid, energy. Lower ambition — PPI is noisier and less tradeable, but it feeds 3.4.

**Gate 3:** replication accuracy report. If 3.4 fails acceptance, stop and fix — nothing downstream is meaningful without it.

## 4. Phase 4 — Nowcast model & validation design (2–3 weeks)

Model class: deliberately boring. Per-component state: proxy signal → component MoM via regularized regression (elastic net) or fixed bridge coefficients where the economics dictate them (gasoline: pass-through is nearly mechanical — impose it, don't estimate it). Aggregate via Phase-3 engine. No end-to-end ML on ~120 monthly observations.

Validation, per ash-ml-doctrine:

* Purged, embargoed walk-forward CV; embargo ≥ 2 months around each test point (YoY transforms create 12-month label overlap — prefer MoM targets throughout).
* All fitting inside folds, including any scaling and the seasonal factors.
* Regime labels (pre-COVID / COVID / 2021–22 inflation / disinflation / 2025–26 tariff) defined by economic state, used ONLY for per-regime honest reporting, never as features fit on future data.
* Report per-regime OOS surprise hit-rate and MAE against all three D2 benchmarks. Publish the failure table with the success table.

Explicit hypotheses to test (pre-registered here):

* H1: Manheim mid-month improves used-car surprise prediction vs consensus. (Expected: yes, weakly — consensus partly embeds it.)
* H2: New-lease rent indices do NOT improve next-print shelter surprise (they lead by ~a year); BLS all-tenant series does.
* H3: The CPI→PCE bridge (3.4) beats consensus core PCE after CPI+PPI release. (Expected: matches, rarely beats — consensus does this too; value is speed and component attribution.)
* H4: Freight/commodity pipeline layer leads core-goods CPI by 1–2 quarters and adds trajectory value, not next-print value.
* H5: Tariff-announcement repricing lags (event-time) improve core-goods forecasts in 2025–26 regime specifically.

**Gate 4:** validation report. Decision: which components carry live weight, which are demoted to "monitor only."

## 5. Phase 5 — Forward scraped layers (ongoing from week ~6, permissive sources only under D1(a))

Principle: scraped layers are forward-only accumulators. They enter the model only after ≥6 months of overlap with their published proxy and a passing bridge regression (stable beta, no level drift). Until then they are dashboards, not features.

5.1 Basket specs (frozen documents, one per source): item identifiers, collection time-of-day, dedup rules, missing-item substitution protocol (mirror BLS item-replacement logic), churn handling via matched-model with explicit imputation for exits.

5.2 Priority order given D1(a): (1) chain menu prices from chains' own sites; (2) Google Flights fixed city-pairs; (3) GoodRx/Cost-Plus/NADAC drug basket; (4) CMS hospital transparency file parser (bulk public files — the naru showcase: large, messy, mandated-public, deterministic parsing); (5) streaming/subscription tracker; (6) delivery markup spread (Uber Eats vs in-store, same restaurant same item) — novel series, collect from day 1 even though it can't be validated for months.

5.3 Every scraper: robots.txt + ToS review logged in the source's license note; rate limits well under human-browsing intensity; no auth walls, no CAPTCHA circumvention, no screenshot-around-blockers. A blocked source is replaced by its backup column, not fought.

5.4 QA: daily anomaly detection (basket count, price-jump z-scores, dedup collision rate) with alerting; a silent scraper failure that poisons three weeks of index is the most likely operational death.

## 6. Phase 6 — Backtest & evaluation harness (parallel with 4–5)

6.1 Event-study framing: for each historical print, assemble the exact information set as of T-1 (release calendar from 2.3), produce the forecast, log surprise prediction vs realized surprise.

6.2 Attribution: every forecast decomposes into component contributions ("this month's upside risk: used cars +2.1bp vs consensus, airfares −1.3bp"). The attribution table is the product; the headline number is marketing.

6.3 Reporting artifact: monthly one-pager auto-generated pre-print — nowcast, surprise direction + confidence, component attribution, regime context, and running OOS scorecard vs benchmarks (including misses, prominently).

## 7. Phase 7 — Positioning & use (after ≥6 live prints)

* Paper track only until the OOS scorecard beats D2 benchmarks over ≥6 consecutive prints.
* Under D1(a): publishable as an open research series (aggregate index + methodology, not raw scraped data — redistribution of scraped micro-data is a separate legal question; publish indices only).
* Fed-signal integration: hawk/dove scorer provides regime context for surprise pricing (a +5bp core surprise means different bp of rates move under different FOMC reaction functions) — this is a separate small study, not part of the nowcast.

## Timeline & effort (realistic, solo, part-time)

* Weeks 1–2: Phase 0–1. Weeks 3–5: Phase 2. Weeks 5–8: Phase 3. Weeks 8–11: Phase 4 + 6. Week 6 onward: Phase 5 accumulating. Month ~6: first honest forward evaluation possible. Anyone promising a validated scraper-based edge in under two quarters is describing look-ahead bias.

## Known kill-risks (stated up front)

* K1: 3.4 bridge fails Tier-1/Tier-2 acceptance → whole PCE story reduces to "another CPI forecaster."
* K1b: analyst contributions leak into core repo → IP taint; enforce D1b mechanically (repo permissions, no shared drafts of code).
* K2: Nothing beats consensus OOS (likely for headline; component attribution may still survive as the product).
* K3: SA replication error swamps component signal for small-weight items.
* K4: Scraper maintenance burden exceeds part-time capacity → shrink to top-3 baskets rather than run 10 badly.
