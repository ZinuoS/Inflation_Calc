# PCE-bridge acceptance report (Session 3B, Task 2) — **FAIL (both tiers)**

The CPI/PPI→core-PCE bridge is evaluated over the trailing 5 years against **first-release**
PCEPILFE MoM (`first_release_mom`, the value BEA first printed), forecast_time = each month's
CPI release date (post CPI+PPI). Shutdown/unreleased months skipped-and-counted. The bridge
has **no fitted parameters** (frozen 2022 CPI-RI proxy weights; imputed terms frozen at
documented values), so there is no estimation window to leak.

## Verdict

| tier | threshold | result | pass |
|---|---|---|:--:|
| **Tier 1** | MAE ≤ 2.0 bp (stretch 1.5 ex-COVID) | **MAE = 12.2 bp** (ex-COVID 12.3) | ❌ |
| **Tier 2** | ≥ 85% correct side of the 0.1% rounding boundary | **27.5%** (40 graded, 24 coin-flip) | ❌ |

n = 64 months, 1 skipped. Per-era: pre-2023 MAE 14.7 bp, post-2023 10.6 bp, February 10.7 bp.
The **2026 out-of-sample holdout** (`holdout_2026.md`) fails identically (MAE 11.4 bp, 0/5
correct side). This is not a near miss — the bridge is off by ~6× the Tier-1 bar.

## Ranked diagnosis — the cause is the missing BEA PCE weights, not the assembly

The bridge assembles component price relatives correctly (the CPI/PPI machinery reconstructs
the official *aggregates* to ≤0.7 bp — `holdout_2026.md` §a). The failure is entirely in the
**weights**: `bea_pce_detail` (Table 2.4.5U) is BEA-API-key-blocked and not publicly
downloadable, so the gate runs on **CPI-relative-importance proxy weights** (explicitly
labeled). Three structural defects, ranked by impact:

1. **Shelter is over-weighted ~3×.** Rent+OER are **46% of the proxy's core weight** (CPI RIs)
   versus ~15–18% in core PCE. Shelter inflation ran hot 2021–2024, so the bridge inherits a
   large positive bias whenever shelter outruns the rest. *Evidence:* mean signed error
   **+10.3 bp** across 2020–2025; the biggest single-month contributor in the 2021 misses is
   OER/used-vehicles carrying CPI weights PCE does not assign.
2. **PPI-priced healthcare is ~zero-weighted.** The proxy weights sum to only **71.6%** of core
   because physician/hospital/nursing/home-health (PPI-relative, ~22% of *core PCE*) and the
   imputed financial/NPISH components have **no CPI relative importance** — the CPI-RI proxy
   literally cannot see them. The bridge is blind to ~30% of core PCE by weight.
3. **The error changes sign across regimes** — over-predicting in the 2020–22 shelter surge
   (+10 bp) and **under-predicting in the 2026 tariff regime** (−8 to −16 bp; `holdout_2026.md`
   §b). A constant calibration offset cannot fix a sign-flipping, regime-dependent error;
   only correct weights can. This is why we did **not** bolt on a frozen bias term (it would
   memorize one regime and fail the next — the exact failure mode the gate guards against).

Secondary, smaller contributors (documented, not the binding constraint): ~31% of core weight
is still read latest-vintage (non-ALFRED feeders + PPI), the Fisher aggregation is a Laspeyres
approximation (BEA nominal detail blocked), and conceptual CPI-vs-PCE basis gaps on the
low-confidence rows (used vehicles gross-vs-margin, pharma payer mix). None of these move the
verdict; the weights do.

## What would fix it (the K1 evidence for Ash)

- **Necessary and likely sufficient: real BEA PCE weights** (Table 2.4.5U) via the BEA API key.
  That single input corrects the shelter over-weight *and* the zero-weighted healthcare — the
  two effects that produce >90% of the miss. It also unblocks the chain-Fisher nominal legs and
  per-component attribution (Table 2.4.4U), turning degraded attribution into verified.
- Attribution of individual misses is **degraded** (Task 0): without BEA per-component price
  detail we can rank the CPI/PPI drivers of a miss but cannot verify them; imputed/equity
  components are marked unattributable.

**Gate stopped here.** Per the session contract, the K1 kill/continue decision on the bridge is
Ash's, not the model's. No progression to Task 3 (the analyst notebook) on a failed gate.
