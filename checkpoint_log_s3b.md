# Session 3B checkpoint log — CPI/PPI → PCE bridge & acceptance gate

## TASK 0 — BEA conditional
`.env` checked 2026-07-20: **BEA_API_KEY absent.** Confirmed BEA underlying detail is NOT
publicly downloadable without the key — API needs the key; the flatfile ZIP paths return HTML
/ 403 and the iTable is JS-gated (rule 5: a blocked source is not fought). So `bea_pce_detail`
stays SKIPPED. Consequence: validation runs against headline **PCEPILFE** vintages only, and
**component-level attribution of bridge misses is degraded** (no BEA 2.4.4U price detail).

## TASK 1 — src/nowcast/pce_bridge.py + component inventory · CHECKPOINT 1

Bridge assembled: reads first-release SA CPI/PPI component relatives (vintaged via timebase,
else latest-vintage-flagged), Laspeyres-weighted (Fisher approximation) with PCE weights;
imputed components as documented frozen approximations. `assemble_core_pce_mom`,
`component_inventory`, `pce_weights`, per-component `ComponentValue` with vintage flag +
covered / latest-vintage weight share. 6 tests green.

### Component inventory (34 core): 20 implemented · 12 approximated · 2 absent

Three structural data gaps make the current bridge a DEGRADED assembler — a gate run now would
mostly measure these, not bridge skill:

1. **PCE weights — BLOCKED (bea_pce_detail, Table 2.4.5U).** No key; not publicly downloadable.
   Fallback = CPI-relative-importance PROXY weights (frozen 2022), loudly flagged. CPI and PCE
   weights diverge most exactly where the bridge is hardest (healthcare via third-party payers,
   financial services, NPISH), so the proxy is worst where it matters most.
2. **First-release vintages — only 5 of ~50 feeders.** Only SEHA, SEHC, SETA01, SETA02, SETB01
   (rent/OER/vehicles/gasoline) are ALFRED-vintaged. The other ~45 CPI and all PPI feeders read
   **latest-vintage** (leakage-exposed to the annual Feb seasonal restatement). Smoke test
   (2024-09): ~43% of core weight read latest-vintage.
3. **Fisher aggregation** needs both-period BEA nominal detail (blocked) → **Laspeyres approx**.
   **S&P-500 path** (portfolio_management post-2022-12; financial_services_without_payment) is
   **not ingested** → those components absent/approximated. 8 CPI SA strata
   (SEED, SEEE02, SEGC, SEGD04, SEMG, SERD02, SETF, SETG03) were never loaded → their components
   drop. Smoke test: only ~64% of core weight priced.

DECISIONS NEEDED before Task 2 (the gate) — see checkpoint message. Waiting.

## TASK 1 (unblock, option B) + TASK 2 GATE + TASK 2b HOLDOUT · CHECKPOINT 2 — **FAIL**

**Inputs ingested (option B):** 14 ALFRED-archived CPI feeders → observations (first-release);
8 NSA-only strata → official_current; S&P-500 equity path (FRED SP500) → proxy_observations
(pipelines/equity_path, licensing-clean note). Bridge updated: dynamic vintage detection,
SA-or-NSA resolution (NSA unrevised=first-release), S&P path for portfolio-mgmt(post-2022) +
financial-services. Inventory now 31 implemented / 3 approximated, **100% core weight priced,
latest-vintage 31% (was 43%)**. 30 feeders not on FRED → latest-vintage; PPI no vintages.

**TASK 2 GATE (trailing 5y, first-release PCEPILFE via first_release_mom):**
- TIER 1: **MAE 12.2bp** (need ≤2.0) — FAIL. TIER 2: **27.5% correct side** (need ≥85) — FAIL.
- Root cause = CPI-RI PROXY WEIGHTS (BEA blocked): shelter=46% of proxy core wt (PCE ~15-18%);
  proxy sums to only 71.6% → PPI-priced healthcare (~22% core PCE) + financial/NPISH get ~0 wt.
  Mean signed +10.3bp (over-predict 2020-22 shelter surge). NO calibration term added — error
  SIGN-FLIPS by regime (see 2026), which a frozen offset can't fix.

**TASK 2b HOLDOUT (2026, tariff regime, strictly OOS):**
- §a CPI machinery: headline NSA 0.02 / SA 0.39bp, core NSA 0.02 / SA 0.71bp — **machinery
  PASSES OOS** (2025 weights, 2026 RI table unpublished). Isolates failure to PCE weights.
- §b bridge holdout: 5 months, **MAE 11.4bp, 0/5 correct side**, UNDER-predicts (−7..−16bp) —
  opposite sign to 2020-22 → regime-dependent weight error confirmed.
- §c PPI machinery: NOT RUN — PPI FD weights not ingested (same gap class).

docs/pce_bridge_acceptance.md (FAIL + ranked diagnosis), docs/holdout_2026.md. pce_bridge.py,
pce_acceptance.py, equity_path pipeline, test_pce_bridge/test_pce_acceptance (10 tests).
**K1 kill/continue is Ash's. STOPPED — no Task 3 on a failed gate. What would fix: BEA key.**

## TASK 2d — proxy information-timing audit + availability calendar (Session-4-binding)

Closed the PROXY side of the firewall (mirror of official-side timebase).
- (a) `publication` block added to every proxy spec.yaml (9 DB sources + apartment_list):
  kind (point_in_time/scheduled/estimated), rule, lag_days, observed_asof_estimated, CITE.
- (b) `src/nowcast/proxy_timebase.py`: `observed_asof(source,period)` materializes the arrival
  date from the rule; `proxy_asof(source,ft,series_key)` returns only obs with observed_asof<=ft.
  **STANDING RULE: Session-4 features MUST read via proxy_asof, never proxy_observations.**
- (c) Adversarial tests (test_proxy_timebase.py, 10): request between ref-period-end and
  observed_asof → not-yet-published obs withheld, prior returned. Same invalidation language.
- (d) docs/availability_calendar.md: per-print T-minus timeline (CPI/PPI/PCE). Worked M=2025-05:
  Manheim mid-month T-25, EIA final week T-15, Manheim full-month + NADAC T-4, CPI T-0; bridge
  PCE call on CPI-day ~15d before PCE print; ZORI lands T+14 (leading, next print). "Last useful
  update" per print documented.
- (e) VERIFIED against reality: Manheim archive URLs /YYYY/MM/ = M+1 (Jan→/02, Feb→/03, Mar→/04
  2025, from provenance.json — all 11 harvested files); EIA GDFU notice (Mon 8am collect, Mon PM/
  Tue 10am publish). Rules are evidence-backed, not assumed. docs/proxy_timing_audit.md.

Note: observed_asof is rule-materialized (not a stored column) — true per-obs press dates aren't
recorded across full history; rule is the auditable form, verified. revised_latest_only sources
carry ESTIMATED observed_asof (+7d conservatism) → still optimism-flagged.

## BEA-INGESTION SESSION — HALTED AT TASK 0 (BEA_API_KEY still absent)

2026-07-21: BEA_API_KEY absent from .env (0 BEA lines) and live env. Per the session contract
("absent → STOP immediately, no second degraded gate"), HALTED before Task 0 ingestion. No
2.4.5U/2.4.4U pull, no bridge rebuild, no re-run of the gate. **Standing verdict is unchanged:
the degraded-input gate FAIL (docs/pce_bridge_acceptance.md) remains the recorded outcome.**
KEEPA_API_KEY also absent → Keepa stays SKIPPED (Task 0c). Task 0b (observed_asof_recorded
forward-capture) and Task 4 (commit/report/push) not started — awaiting direction: provide the
BEA key to run the valid gate, or authorize Task 4 on the standing degraded verdict.

## BEA INGESTION RESUMED (key activated 2026-07-21) — TASK 0 · CHECKPOINT 0

BEA_API_KEY activated and validated (NIUnderlyingDetail reachable). Ingested via new
pipeline pipelines/bea_pce_detail (fetch.py + spec + license_note + publication block;
loaded through the shared official_loader naru artifact; BEA parse unit-tested).

**Rows/ranges:** 152,478 rows into official_current (source=bea_pce_detail), 2010-01..2026-05,
774 series = 380 nominal (RC, Table 2.4.5U weights) + 378 price (RG, Table 2.4.4U). RC/RG
suffixes keep nominal and price distinct — no collision.

**Crosswalk coverage: 34/34 core bridge components mapped (100%)**, each to a BEA stem with
bea_weight_code (RC) + bea_price_code (RG) in mapping.yaml; all have 197 monthly obs both
sides. WEIGHT SANITY (2024 nominal shares) — the pre-registered fix confirmed at weight level:
shelter 46%(proxy)->19.7%(BEA), healthcare ~0%->24.4% (hospital 9.4, physician 5.0, pharma 4.3,
+ins/dental/nursing/home-health); top: OER 15.0, hospitals 9.4, food-services 9.0.

**Imperfect mappings (4, documented as bea_mapping_note; none structural):**
- physician_outpatient_services->DPHY (physician svcs; outpatient-center detail DOUS not split)
- motor_vehicle_services->DMVS (MV insurance SETE sits in BEA DTIN not DMVS — mild scope gap)
- other_transportation_services->DGRD (ground transport incl. intracity; CPI SETG splits differ)
- health_insurance_margin->DHIN (exact concept match: BEA premiums-less-benefits margin)

**0b (forward-capture):** provenance (meta_fetch_provenance.retrieved_at_utc) records today's
BEA/all pulls; per-obs observed_asof_recorded column + rule-vs-recorded divergence check
specified for Session 5 QA (forward mechanism; noted, not built this checkpoint).
**0c (Keepa):** KEEPA_API_KEY absent -> keepa SKIPPED; H7/H8 will run degraded on EIA+NADAC.

Next: Task 1 (bridge rebuild on true weights, Fisher where nominal legs permit) then Task 2
THE VALID GATE. Awaiting go.

## TASK 1 (bridge rebuild on true BEA weights) + TASK 2 (THE VALID GATE) · CHECKPOINT 2 — FAIL

Rebuilt pce_bridge on BEA 2.4.5U weights (bea_weights: prior-year annual nominal shares,
vintage-appropriate/structural; documented revision-handling — annual shares barely revise,
bias~0). Two correctness fixes surfaced by activating true weights: (1) PPI healthcare/air
feeders were STALE ending 2015 (BLS 10y API cap) -> re-pulled through 2026; (2) S&P equity path
was a poor price proxy vs BEA 2.4.4U (poor corr, opposite sign) -> reverted portfolio-mgmt
(post-2022) + financial-services to frozen. No calibration terms.

**VALID GATE (BEA weights) vs degraded, trailing 5y:**
| metric | degraded | valid |
|---|--:|--:|
| Tier1 MAE | 12.2 | **9.1** (FAIL, need <=2.0) |
| Tier2 correct-side | 27.5% | **35.4%** (FAIL) |
| mean SIGNED err | +10.3 | **-0.3 (bias GONE)** |
| core weight repr | 71.6% | 95.9% |
| 2026 holdout MAE | 11.4 | 20.9 |

Pre-registered expectation HALF-MET: true weights removed the bias (shelter 46->19.7%,
healthcare 0->24.4%) but MAE only 12->9bp (not low-single-digits) — activating healthcare/
financial weights EXPOSED component proxy-tracking error. **Ranked diagnosis (verified vs BEA
2.4.4U, attribution_vs_bea):** 1) financial_service_charges_fees 5.2bp (CPI SEGD05 wildly
volatile: +676bp vs BEA +6bp — genuine CPI/PCE basis, not a bug), 2) portfolio_mgmt 4.0bp
(frozen, unforecastable), 3) air_transportation 3.0bp (PPI>>PCE volatility), 4) npish 2.9bp
(frozen trend), 5) financial-without-payment 2.6bp (frozen). ~5 service components (~15% wt)
drive the dispersion; other ~85% tracks well & unbiased.

2026 holdout WORSE (20.9bp) — tariff regime amplifies the same components; CPI machinery (§a)
still nails aggregates OOS, isolating it to bridge component-proxy error. pce_bridge_acceptance.md
+ holdout_2026.md updated. attribution_vs_bea added. 12 bridge/gate tests green.
**FAIL both tiers. STOPPED — no Task 3. K1 (kill/monitor/authorize-proxy-work) is Ash's call.**

## K1 → CONTINUE RESCOPED. TASK R1 — H9 PRE-REGISTRATION (written BEFORE any code/audit/results)

Rescope: Instrument A (full core, unbiased monitor) + Instrument B (trackable core = core ex 5
residue: financial_service_charges_fees, portfolio_management, air_transportation,
npish_final_consumption, financial_services_without_payment). Original single-instrument FAIL stands.

**H9 — pre-registered expectations (falsifiable; results in CHECKPOINT R1/R2):**

H9a — SOURCE-MAPPING AUDIT (each correction must cite NIPA Handbook ch.5 / published source tables;
no citation → does not ship):
- financial_service_charges_fees: EXPECT BEA does NOT price this from CPI SEGD05. Hypothesis: BEA
  uses a mix incl. explicit bank service charges from CPI/other + smoothing; SEGD05's ±hundreds-bp
  swings should NOT match BEA. FALSIFY if handbook shows BEA uses SEGD05 directly (then keep, record).
- air_transportation: EXPECT BEA prices partly from CPI airfares (SETG01) and/or a smoothed
  series, NOT raw PPI 481111. FALSIFY if handbook shows PPI 481111 is the sole source.
- portfolio_management: EXPECT BEA prices via within-month AVERAGE asset levels × fee margins
  (asset-based), so a month-average equity path (not month-end) should track it. FALSIFY if
  handbook shows a fixed fee-rate index (then frozen/carry is correct).

H9b — TIMING FIX: rebuild equity path as MONTH-AVERAGE of daily S&P (currently monthly-avg via
alignment — verify), test 1-month lag if BEA documents one. EXPECT correlation(equity-path,
DPMIRG) flips CLEARLY POSITIVE (from the current near-zero/negative). FALSIFY: if corr stays
≤0.2, portfolio_management reverts to carry and the finding is recorded (no forcing).

H9c — IMPUTED-LINE CARRY MODELS (npish, financial_services_without_payment, + any residue BEA
smooths): candidates = random-walk carry, AR(1)/AR(k), trailing-12m mean; SELECTED ON pre-2023
DATA ONLY, then FROZEN. EXPECT smooth series → carry/AR cuts each line's mean|contrib| MATERIALLY
vs freeze-at-zero (which had signed bias -2.1/-2.2bp). FALSIFY: if no candidate beats freeze on
pre-2023, keep freeze and record.

RESCOPED GATE THRESHOLDS (set NOW, before R2 results):
- Instrument B (trackable core): Tier1 MAE ≤ 2.5bp, Tier2 ≥ 85% boundary-correct.
- Instrument A (full core): |mean signed err| ≤ 1bp (dispersion band reported, boundary rate
  reported w/o threshold).
- 2026 holdout MANDATORY for both; attribute which fix moved 2026 MAE (20.9bp baseline).
NO touching residue specs after R2 results; NO blending A+B into one headline.

## TASK R1 — H9 SOURCE-MAPPING AUDIT + FROZEN RESPECS · CHECKPOINT R1

Audit vs NIPA Handbook ch.5 Table 5.B (Dec 2024), each correction CITED; empirical corr of
each source vs BEA 2.4.4U actual price is the evidence.

**H9a source-mapping (findings):**
- financial_service_charges: CONFIRMED BEA does NOT use CPI SEGD05. BEA = "CPI for checking
  account and other bank services" (SS68021) + PPI brokerage commissions. Remapped SEGD05→SS68021.
  corr vs BEA DOFI: 0.17→0.32 — improved but still weak (BEA blends+smooths) -> stays RESIDUE.
- air_transportation: FALSIFIED (expected CPI/smoothed). BEA = "PPI domestic scheduled passenger
  air transportation" = PCU481111 = what the bridge already uses (corr 0.70). No change; TRACKABLE.
- portfolio_management: FALSIFIED (expected asset-based avg). BEA = fixed-wt avg of PPI portfolio
  mgmt + PPI investment advice. Old PCU523920523920 discontinued 2022-12; LIVE successor
  PCU5239205239202 (corr 0.82 vs BEA DPMI; investment-advice PCU523940 corr 0.998). S&P path was
  WRONG. Remapped to the successor PPI -> RETURNS to TRACKABLE.

**H9b timing:** MOOT/falsified — BEA prices portfolio via PPI, not an asset path, so the equity
path (any averaging/lag) is the wrong instrument. Reverted; no equity path in the bridge.

**H9c imputed carry (npish, financial_services_without_payment — no market proxy):** frozen DRIFT
= pre-2023 mean MoM (npish +26.38bp, fin-without-payment +54.58bp), selected pre-2023 ONLY,
frozen. Beats freeze-at-zero in pre-2023 MAE (48<51, 51<68) and removes the upward-trend signed
bias. Both stay RESIDUE.

**RESULT — residue shrinks 5→3.** Instrument B (trackable core) = core EX {financial_service_
charges_fees, financial_services_without_payment, npish} (the corr<0.5 / carry-only lines).
portfolio_management + air_transportation REJOIN trackable via the cited source fixes.
Implemented: mapping bea_mapping_note + residue flags + frozen_drift_bp; pce_bridge
exclude_residue (Instrument B) + _drift + is_residue; ingested SS68021 + PCU5239205239202 +
PCU523940523940. No touching residue specs after R2. WAIT for go to R2 (rescoped gates).

## TASK R2 — RESCOPED GATES · CHECKPOINT R2 — B FAILS (precision terminal), A = monitor

Instrument B coverage 89.5% of core wt; residue 10.5% wt / 9.7% of core-MoM variance.
- **Instrument B (trackable, ≤2.5bp/≥85%): FAIL.** 5yr MAE 8.26bp (ex-seam 7.16, seam 14.21),
  Tier2 36.8%; 2026 8.2bp. Ex-seam still 7.16 -> TERMINAL: BEA component prices are commodity-flow
  derivatives of CPI/PPI, ~7bp irreducible divergence even on trackable core. Precision claim dead.
- **Instrument A (full core, |signed|≤1): FAIL (+3.28), carries forward as monitor.** Bias = H9c
  frozen drifts over-correcting OOS (npish+0.98, fin-without-payment+1.85); freeze baseline was
  -0.3 (would pass) -> H9c FALSIFIED OOS. Dispersion [-10,+19]bp. Residue specs NOT reverted (frozen).
- **2026 attribution:** respec cut 2026 full-core MAE 20.9->8.7bp, driven by the portfolio-mgmt
  PPI fix (live successor tracks 2026 swings the frozen/S&P version missed).
pce_bridge_acceptance.md R2 section + additions written. No Task 3 (B failed). WAIT.

## H9c REVERSAL + STANDING OOS REPORT

TASK 1 — H9c REVERSAL (falsified → null, not tuning): reverted npish +
financial_services_without_payment to freeze-at-zero (frozen_drift_bp=0). Instrument A signed
+3.28 → +0.31bp (unbiased; residual vs -0.3 baseline = retained H9a portfolio/financial source
fixes, which are correct). Recorded in pce_bridge_acceptance.md: H9c pre-registered→tested→
FALSIFIED OOS (mechanism: pre-2023 mean over-states post-2022 trend as rates rose), null restored.
SELECTION ASTERISK: falsifying window = eval window → A's 2023+ bias not pristine until forward
prints. PRE-REGISTERED STANDING RULE: residue carry specs re-selected each JANUARY on data through
prior year-end, frozen for the calendar year, every change logged.

TASK 2 — docs/oos_report_1.md (standing, 2023-01→latest). Three-tier honesty: PURE OOS
(CPI/PPI machinery, 0 fitted params), QUASI-OOS (PCE bridge, H9a verified on-window), PRISTINE
(forward prints — none yet, stub). (a) CPI: headline NSA MAE 0.42bp / core NSA 1.12bp (clean
first-release); SA higher (3.98/2.96) — older SA components carry annual restatement, NSA is the
clean measure. (b) PPI FD: NOT BUILT (no FD weights/aggregator) — documented gap, deferred. (c)
PCE Instrument A: mean signed +0.36bp (unbiased), MAE 7.97, 10-90 band [-11.9,+12.7], boundary
39% ex-COINFLIP; side-by-side +3.28→+0.36 (reversal). (d) headline block: machinery ~0.4bp pure
OOS / bridge unbiased ±8bp quasi-OOS monitor / prediction NOT BUILT. 106 tests green.
