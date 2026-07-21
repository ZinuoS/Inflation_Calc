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
