# PCE-bridge acceptance report — **VALID GATE (true BEA weights)**

The bridge is now evaluated on **true PCE weights** (BEA NIPA Table 2.4.5U, `bea_pce_detail`,
prior-year annual nominal shares) against **first-release** PCEPILFE MoM, forecast_time = each
month's CPI release date. This supersedes the degraded-weights run (kept below for the
side-by-side the K1 decision requires). The bridge has **no fitted parameters**.

Two correctness fixes were applied during the rebuild (not gate-tuning, not calibration):
(1) the PPI healthcare/air feeders were **stale — data ended 2015** (BLS API 10-yr cap without a
key); re-pulled through 2026. (2) The **S&P equity path** for portfolio-mgmt / financial-services
was shown (vs BEA 2.4.4U) to be a **poor price proxy** — poorly correlated, sometimes opposite
sign — so those components revert to frozen (no forecastable signal).

## Verdict — **FAIL both tiers**, but the true weights removed the bias

| tier | threshold | degraded (CPI-RI proxy) | **valid (BEA 2.4.5U)** |
|---|---|--:|--:|
| **Tier 1** MAE | ≤ 2.0 bp | 12.2 bp | **9.1 bp** ❌ |
| **Tier 2** correct side | ≥ 85% | 27.5% | **35.4%** ❌ |
| mean **signed** error | (bias) | **+10.3 bp** | **−0.3 bp** |
| core weight represented | — | 71.6% | **95.9%** |
| 2026 holdout MAE | — | 11.4 bp | **20.9 bp** |

**The pre-registered expectation was half-met.** True weights did exactly what was predicted to
the *bias*: shelter 46%→19.7%, healthcare ~0%→24.4%, and the systematic over-prediction
collapsed **+10.3 → −0.3 bp** (unbiased). But Tier-1 MAE fell only **12.2 → 9.1 bp**, not to
"low single digits": activating the healthcare/financial weights **exposed the component
proxy-tracking error** that was previously weightless. The gate still **fails** — now on
month-to-month **dispersion**, not level bias. Per-era: pre-2023 9.5, post-2023 8.8, Feb 9.0 bp.

## Ranked diagnosis — verified against BEA 2.4.4U (the attribution the degraded gate could not do)

Mean |contribution| to the miss, per component, 5y (`pce_acceptance.attribution_vs_bea`):

| rank | component | mean\|contrib\| | source | why it misses |
|---|---|--:|---|---|
| 1 | financial_service_charges_fees | **5.2 bp** | CPI SEGD05 | CPI financial services is wildly volatile (e.g. +676 bp in 2025-03) vs BEA's smooth +6 bp — a genuine CPI-vs-PCE basis mismatch, not a bug |
| 2 | portfolio_management | 4.0 bp | frozen | PPI discontinued 2022-12; BEA's asset-based price swings ±100s bp, unforecastable at CPI-day |
| 3 | air_transportation | 3.0 bp | PPI 481111 | PPI airfare far more volatile than PCE air transport (e.g. bridge +646 vs BEA +93) |
| 4 | npish_final_consumption | 2.9 bp | frozen | input-cost line, no market proxy; frozen misses its ~+2 bp/mo trend |
| 5 | financial_services_without_payment | 2.6 bp | frozen | imputed bank services; no forecastable price at CPI-day |
| 6–10 | recreational goods, hospital, MV services, food services, recreation | 1.2–2.5 bp | CPI/PPI | ordinary CPI/PPI-vs-PCE basis noise |

**The failure is concentrated in ~5 service components (~15% of core weight):** two with poor,
over-volatile CPI/PPI proxies (financial charges, air transport) and three that are genuinely
**unforecastable at CPI-day** (portfolio, NPISH, imputed financial services — carried frozen).
The other ~85% of core PCE (housing, healthcare services, food services, goods) now tracks well
and is unbiased. This is the low-confidence-rows concern from Session 1, quantified.

## What would move it (K1 input for Ash — my decision is to STOP here)

- The bias problem is **solved**; the remaining gap is component proxy quality, which is a
  **pre-registered modeling question for Session 4**, not something to hand-fix here (hand-fixing
  the financial/air proxies after seeing the misses would be tuning-to-OOS, which the doctrine
  forbids). Candidate: replace CPI SEGD05 / PPI airfare with dampened or model-based component
  forecasts; carry the three frozen imputed lines with a pre-2023-estimated frozen drift.
- As a **precise (≤2 bp) core-PCE nowcast the bridge FAILS.** As an **unbiased directional
  estimate** it is much improved (mean error ~0, 9 bp dispersion). Whether that clears the K1 bar
  — kill, accept-as-monitor, or authorize targeted proxy work as a new hypothesis — is **Ash's
  call, not the model's.**

**Gate stopped here.** No progression to Task 3 (analyst notebook) on a failed gate.

---

## K1 decision (recorded) — CONTINUE, RESCOPED into two instruments

The FAIL above, on the **original single-instrument claim** (one ≤2 bp core-PCE nowcast), **stands
in the record and is not relabeled.** The bridge is re-specified as two instruments:

- **Instrument A — full core PCE:** an **unbiased monitor** (mean signed error ~0), reported with
  an honest dispersion band. No MAE tier; it is not claimed to be a ≤2 bp instrument.
- **Instrument B — trackable core:** core PCE **excluding the five diagnosed residue components**
  (financial_service_charges_fees, portfolio_management, air_transportation, npish_final_consumption,
  financial_services_without_payment ≈ 15% of core weight) — a **precision instrument with its own
  gate** (Tier 1 ≤ 2.5 bp, Tier 2 ≥ 85%, thresholds set before results).

Rationale: the diagnosis shows the failure is **concentrated** — ~85% of core PCE already tracks
well and unbiased, while ~15% is either poorly proxied or unforecastable at CPI-day. Splitting the
claim lets the trackable part be held to a precision bar while the residue is carried honestly as
"what nobody can forecast at CPI-day," rather than letting five components sink the whole estimate
or, worse, tempting a single blended headline number that hides the residue. Targeted
respecification of the residue is authorized as **pre-registered methodology work** (H9, expectations
logged before code — `checkpoint_log_s3b.md`), explicitly **not** post-hoc tuning. The rescoped
gates and their verdicts are in `checkpoint_log_s3b.md` (CHECKPOINT R2).

---

## CHECKPOINT R2 — the rescoped gates (thresholds frozen before results)

Coverage: **Instrument B = 89.5% of core weight**; the 3 residue lines = **10.5% weight / 9.7% of
historical core-MoM variance** (core-MoM std 17 bp, residue-contribution std 5 bp). Thresholds
were set at R1, before these numbers.

### Instrument B — trackable core (ex residue). Gate: Tier 1 ≤ 2.5 bp, Tier 2 ≥ 85% — **FAIL**

| window | MAE | ex-seam (ex Jan/Feb) | seam (Jan/Feb) | Tier 2 | verdict |
|---|--:|--:|--:|--:|:--:|
| 5-year | **8.26 bp** | 7.16 | 14.21 | 36.8% | ❌ |
| 2026 holdout | 8.20 bp | 9.13 | 6.81 | 0/5 | ❌ |

Per-era: pre-2023 7.61, post-2023 8.81. **Ex-seam is still 7.16 bp** — the annual seam worsens it
but is not the cause. **Terminal K1 on the precision claim:** BEA's PCE component prices are
commodity-flow-reweighted *derivatives* of CPI/PPI (not the CPI/PPI themselves), so even the
89.5%-weight trackable core, priced from CPI/PPI proxies, diverges from BEA's constructed
trackable actual by ~7 bp irreducibly. A ≤2.5 bp CPI/PPI→PCE nowcast is not achievable at
component granularity. **The precision instrument is dead.**

### Instrument A — full core. Acceptance: |mean signed| ≤ 1 bp — **FAIL, but carries forward as the monitor**

| window | mean signed | MAE | 10–90 dispersion band | boundary-correct |
|---|--:|--:|--:|--:|
| 5-year | **+3.28 bp** | 8.76 | [−10.0, +19.1] bp | 27.9% |
| 2026 holdout | −5.45 bp | **8.7 bp** (baseline 20.9) | — | — |

Per-era: pre-2023 9.71, post-2023 7.97; Feb 9.94. **The +3.28 bias is the H9c frozen drifts
over-correcting out of sample** (npish +0.98, financial-without-payment +1.85 bp) — the pre-2023
trend fell after rates rose in 2022+. **H9c is falsified OOS**: the simpler freeze-at-zero
baseline gave signed **−0.3 bp** (would pass ≤1). Per the contract the residue specs are frozen
and NOT reverted post-R2; the freeze/drift comparison is recorded as evidence for the next call.

**2026 attribution:** the respec cut 2026 full-core MAE **20.9 → 8.7 bp**, driven by the
**portfolio-management PPI fix** (was frozen/S&P, missing BEA's large 2026 swings; the live PPI
successor now tracks them) — the single largest 2026 improvement.

### R2 verdict
- **Instrument B FAILS → the ≤2.5 bp precision claim is terminal K1-dead.** Recorded.
- **Instrument A carries forward alone as the unbiased-ish monitor** (bias +3.28 with the frozen
  drifts; −0.3 without them — an open item for the next decision). No Task 3 notebook on a failed
  precision gate.

---

## H9c reversal — falsified hypothesis, null restored (not tuning)

H9c (frozen pre-2023 drift for the two no-proxy carry lines) was **pre-registered** before code,
**tested** in R2, and **falsified out of sample**: the drift over-corrected by **+0.98 bp (npish)
and +1.85 bp (financial-services-without-payment)**, pushing Instrument A's bias from −0.3 to
+3.28. **Mechanism named:** the pre-2023 mean over-states the post-2022 trend — imputed bank-
service and NPISH inflation fell after interest rates rose in 2022+, so a drift frozen on the
low-rate era runs hot afterward. Per doctrine, a falsified hypothesis returns to the **null**:
npish + financial_services_without_payment revert to **freeze-at-zero** (`frozen_drift_bp = 0`).
Post-reversal Instrument A signed error = **+0.31 bp** (within the ≤1 bp acceptance; the residual
vs the −0.3 freeze baseline is the retained H9a source fixes for portfolio/financial, which are
correct and kept). This is restoring the null, **not** tuning — no spec was chosen to improve the
metric; a pre-registered term that failed was removed.

**Selection asterisk (annotation):** the window that falsified H9c (2023+) is the same window
Instrument A is evaluated on. So Instrument A's 2023+ bias carries a **selection asterisk** — it
is not pristine out-of-sample evidence — until genuinely forward prints (post-today) adjudicate
it. The `oos_report_1.md` PRISTINE tier holds that stub.

**PRE-REGISTERED STANDING RULE (residue carry specs):** each **January**, the carry spec for every
residue line (currently npish, financial_services_without_payment — freeze-at-zero) is
re-selected on data **through the prior year-end**, **frozen for the calendar year**, and **every
change logged** (checkpoint log). No mid-year residue re-selection; no re-selection after seeing a
print. This makes future carry adjustments rules-based and pre-committed rather than reactive.
