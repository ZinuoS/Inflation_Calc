# OOS deviation report #1 — reconstruction vs official first-release

**Standing report.** Window: **2023-01 → latest released print** (CPI/PPI ref through 2026-06,
PCE ref through 2026-05; enumerated from `release_calendar`). Updated as prints land.

## Three-tier honesty labels (do not blend across tiers in any summary)

- **PURE OOS** — CPI/PPI aggregation machinery: **zero fitted parameters** (`aggregate.py` =
  published-weight Laspeyres; NSA is unrevised = first-release). Nothing was estimated, so every
  month is genuine out-of-sample.
- **QUASI-OOS** — the PCE bridge: no fitted parameters either, but the H9a source specs
  (portfolio→PPI, financial→bank-services CPI) were **verified on this same window**, and the
  H9c reversal was **adjudicated on it** — so the 2023+ bridge bias carries a **selection
  asterisk** until pristine forward prints exist.
- **PRISTINE** — forward prints released *after* today (2026-07-21), untouched by any spec or
  audit. **None yet.** Stub below; this is the only tier that can eventually validate predictive
  claims, and the prediction layer itself is **not built** (Session 4).

## Headline — the three instruments, one honest line each

| instrument | claim | tier |
|---|---|---|
| **CPI aggregation machinery** | reconstructs official first-release **headline NSA to ~0.4 bp, core NSA ~1.1 bp** | PURE OOS |
| **PCE bridge (Instrument A, full core)** | **unbiased** monitor (mean signed ~0), **±8 bp** month dispersion — a direction/level monitor, NOT a ≤2 bp instrument | QUASI-OOS |
| **Prediction layer** (pre-print CPI/PPI forecast) | **NOT BUILT** — Session 4; no forward skill claimed or measured | PRISTINE (empty) |

### a. CPI machinery — PURE OOS (deviation |bp|, reconstruction vs official first-release)

| month | era | seam | HL-NSA | HL-SA | Core-NSA | Core-SA |
|---|---|:--:|--:|--:|--:|--:|
| 2023-01 | 23-25 | ◆ | 0.25 | 3.39 | 1.72 | 2.67 |
| 2023-02 | 23-25 | ◆ | 0.02 | 2.24 | 3.43 | 6.63 |
| 2023-03 | 23-25 |  | 0.33 | 7.56 | 0.51 | 3.44 |
| 2023-04 | 23-25 |  | 1.43 | 3.17 | 1.30 | 4.05 |
| 2023-05 | 23-25 |  | 0.17 | 4.16 | 0.88 | 7.20 |
| 2023-06 | 23-25 |  | 0.05 | 4.44 | 1.37 | 7.44 |
| 2023-07 | 23-25 |  | 0.10 | 3.32 | 0.55 | 6.69 |
| 2023-08 | 23-25 |  | 0.83 | 16.40 | 2.06 | 4.91 |
| 2023-09 | 23-25 |  | 1.08 | 0.56 | 6.11 | 2.26 |
| 2023-10 | 23-25 |  | 0.98 | 10.25 | 3.96 | 9.27 |
| 2023-11 | 23-25 |  | 1.00 | 5.71 | 1.21 | 2.74 |
| 2023-12 | 23-25 |  | 1.21 | 10.65 | 1.75 | 3.51 |
| 2024-01 | 23-25 | ◆ | 0.86 | 1.29 | 2.69 | 5.64 |
| 2024-02 | 23-25 | ◆ | 0.59 | 3.09 | 1.81 | 5.59 |
| 2024-03 | 23-25 |  | 1.21 | 6.83 | 0.06 | 2.09 |
| 2024-04 | 23-25 |  | 1.02 | 9.68 | 1.14 | 3.32 |
| 2024-05 | 23-25 |  | 0.12 | 3.97 | 0.31 | 4.18 |
| 2024-06 | 23-25 |  | 0.98 | 0.87 | 2.59 | 0.65 |
| 2024-07 | 23-25 |  | 0.35 | 1.04 | 3.29 | 0.81 |
| 2024-08 | 23-25 |  | 0.77 | 3.19 | 1.69 | 2.39 |
| 2024-09 | 23-25 |  | 0.64 | 3.24 | 0.16 | 0.43 |
| 2024-10 | 23-25 |  | 0.05 | 4.22 | 1.84 | 4.34 |
| 2024-11 | 23-25 |  | 0.24 | 2.76 | 0.80 | 0.67 |
| 2024-12 | 23-25 |  | 0.31 | 5.01 | 1.00 | 2.40 |
| 2025-01 | 23-25 | ◆ | 0.30 | 5.76 | 0.23 | 5.13 |
| 2025-02 | 23-25 | ◆ | 0.34 | 1.22 | 0.41 | 3.09 |
| 2025-03 | 23-25 |  | 0.08 | 9.10 | 0.00 | 1.88 |
| 2025-04 | 23-25 |  | 0.05 | 5.45 | 0.14 | 0.45 |
| 2025-05 | 23-25 |  | 0.20 | 2.37 | 0.19 | 0.28 |
| 2025-06 | 23-25 |  | 0.16 | 3.13 | 0.12 | 1.18 |
| 2025-07 | 23-25 |  | 0.19 | 3.22 | 0.13 | 0.79 |
| 2025-08 | 23-25 |  | 0.11 | 3.69 | 0.01 | 3.32 |
| 2025-09 | 23-25 |  | 0.31 | 1.96 | 0.16 | 1.59 |
| 2025-10 | 23-25 |  | — | — | — | — |
| 2025-11 | 23-25 |  | — | — | — | — |
| 2025-12 | 23-25 |  | — | — | — | — |
| 2026-01 | 2026 | ◆ | 0.01 | 0.22 | 0.01 | 2.82 |
| 2026-02 | 2026 | ◆ | 0.01 | 0.04 | 0.01 | 0.58 |
| 2026-03 | 2026 |  | 0.01 | 1.02 | 0.01 | 0.27 |
| 2026-04 | 2026 |  | 0.03 | 0.22 | 0.02 | 0.30 |
| 2026-05 | 2026 |  | 0.02 | 0.23 | 0.02 | 0.01 |
| 2026-06 | 2026 |  | 0.01 | 0.63 | 0.03 | 0.27 |

**Summary (|dev| bp):**

| series | MAE | median | max (month) | ex-seam MAE | seam MAE |
|---|--:|--:|--:|--:|--:|
| headline NSA | 0.42 | 0.25 | 1.43 (2023-04) | 0.45 | 0.30 |
| headline SA | 3.98 | 3.22 | 16.40 (2023-08) | 4.45 | 2.15 |
| core NSA | 1.12 | 0.55 | 6.11 (2023-09) | 1.08 | 1.29 |
| core SA | 2.96 | 2.67 | 9.27 (2023-10) | 2.68 | 4.02 |

### b. PPI final-demand machinery — BUILT AND MEASURED (H15b, data-quality sprint)

The gap is closed. Published **FD-ID relative importances** (`bls.gov/web/ppi/ppi-fdgrouprel.xlsx`,
Dec-2024 weights, posted 2026-06-11) give a **complete non-overlapping 33-group leaf partition
summing to exactly 100.000** — the same coarsest-complete-partition doctrine as the CPI side. The 33
NSA leaf series (`WPUFD…`) run through `index_math`'s price-updated Laspeyres and are compared to
official final demand (`WPUFD4`) NSA MoM.

| PPI FD replication (NSA MoM) | value |
|---|--:|
| **MAE, 2017-02 → 2025-12 (n=107)** | **3.89 bp** |
| **MAE, 2023+ (n=36)** | **1.93 bp** |
| median / p90 / max | 2.47 / 8.43 / 29.45 bp |
| partition coverage | **100.0%** of FD weight |

**2023+ at 1.93 bp is rounding-floor territory**, matching the pre-registered target and the CPI
result's shape (headline NSA 0.50 bp). The residual concentrates in the **2022 energy spike**
(worst: 2022-07 +29.5, 2022-06 −20.3 bp) — the same **weight-vintage era effect** as the CPI
replication (a Dec-2024 weight set cannot reproduce 2022 relative importances), not a machinery
error. Measurement/replication only: **no forward PPI skill is claimed or measured**, so this adds
no predictive claim — it closes a *replication* gap.

*Caveat, stated:* BLS's public API caps history at 10 years without a registration key, so the
window starts 2017-02; FD leaf series were retrieved in two batches (25-series/request cap).

### c. PCE bridge — Instrument A (full core, post-H9c-reversal), CPI-day information only — QUASI-OOS

Bridge call vs official **first-release** core PCE (PCEPILFE) MoM. Residue column = the 3
residue lines' combined signed contribution (bp) to the deviation, shown when |dev|>2 (it can
exceed the deviation when residue and trackable components offset — that is the point of
carrying it separately). ◆ = February factor-seam.

| month | era | seam | bridge (bp) | actual (bp) | dev (bp) | boundary | residue (bp) |
|---|---|:--:|--:|--:|--:|---|--:|
| 2023-01 | 2023-25 |  | +54.9 | +57.1 | -2.2 | COIN-FLIP | -4.7 |
| 2023-02 | 2023-25 | ◆ | +39.1 | +30.0 | +9.2 | MISS | -1.2 |
| 2023-03 | 2023-25 |  | +36.9 | +28.1 | +8.8 | MISS | -0.3 |
| 2023-04 | 2023-25 |  | +36.6 | +38.0 | -1.4 | correct |  |
| 2023-05 | 2023-25 |  | +28.4 | +31.5 | -3.1 | correct | +1.1 |
| 2023-06 | 2023-25 |  | +22.0 | +16.6 | +5.4 | correct | -10.1 |
| 2023-07 | 2023-25 |  | +42.3 | +21.6 | +20.7 | MISS | -2.1 |
| 2023-08 | 2023-25 |  | +4.0 | +14.5 | -10.5 | COIN-FLIP | -3.6 |
| 2023-09 | 2023-25 |  | +20.0 | +29.9 | -9.9 | MISS | -1.7 |
| 2023-10 | 2023-25 |  | +32.8 | +16.4 | +16.5 | MISS | +6.6 |
| 2023-11 | 2023-25 |  | +10.9 | +5.8 | +5.1 | correct | +1.1 |
| 2023-12 | 2023-25 |  | +29.2 | +17.1 | +12.1 | MISS | -5.4 |
| 2024-01 | 2023-25 |  | +66.0 | +41.6 | +24.5 | COIN-FLIP | -15.6 |
| 2024-02 | 2023-25 | ◆ | +19.2 | +26.1 | -6.9 | MISS | -4.6 |
| 2024-03 | 2023-25 |  | +27.6 | +31.7 | -4.0 | correct | -2.8 |
| 2024-04 | 2023-25 |  | +25.4 | +24.9 | +0.4 | COIN-FLIP |  |
| 2024-05 | 2023-25 |  | +13.8 | +8.3 | +5.5 | COIN-FLIP | -1.3 |
| 2024-06 | 2023-25 |  | +16.1 | +18.2 | -2.1 | COIN-FLIP | -4.8 |
| 2024-07 | 2023-25 |  | +13.9 | +16.1 | -2.2 | COIN-FLIP | -8.8 |
| 2024-08 | 2023-25 |  | +20.9 | +13.0 | +7.9 | MISS | +4.0 |
| 2024-09 | 2023-25 |  | +13.4 | +25.4 | -11.9 | MISS | -2.5 |
| 2024-10 | 2023-25 |  | +43.2 | +27.3 | +15.9 | MISS | -7.6 |
| 2024-11 | 2023-25 |  | +16.4 | +11.5 | +5.0 | COIN-FLIP | -1.8 |
| 2024-12 | 2023-25 |  | +23.9 | +15.6 | +8.3 | COIN-FLIP | -5.1 |
| 2025-01 | 2023-25 |  | +40.8 | +28.5 | +12.3 | MISS | -3.6 |
| 2025-02 | 2023-25 | ◆ | +24.7 | +36.5 | -11.8 | COIN-FLIP | -12.6 |
| 2025-03 | 2023-25 |  | +2.5 | +2.8 | -0.3 | correct |  |
| 2025-04 | 2023-25 |  | +13.6 | +11.6 | +2.0 | COIN-FLIP |  |
| 2025-05 | 2023-25 |  | +9.2 | +17.9 | -8.7 | MISS | -1.8 |
| 2025-06 | 2023-25 |  | +22.5 | +25.6 | -3.1 | MISS | -1.2 |
| 2025-07 | 2023-25 |  | +29.4 | +27.3 | +2.0 | correct | -13.5 |
| 2025-08 | 2023-25 |  | +23.2 | +22.7 | +0.5 | correct |  |
| 2025-09 | 2023-25 |  | +16.6 | +19.8 | -3.2 | correct | -0.7 |
| 2025-11 | 2023-25 |  | -0.5 | +16.0 | -16.5 | MISS | +1.9 |
| 2025-12 | 2023-25 |  | +28.0 | +35.5 | -7.6 | MISS | -2.3 |
| 2026-01 | 2026 |  | +40.9 | +36.4 | +4.6 | correct | -9.1 |
| 2026-02 | 2026 | ◆ | +19.4 | +36.7 | -17.2 | MISS | -3.1 |
| 2026-03 | 2026 |  | +14.1 | +29.3 | -15.2 | COIN-FLIP | -3.2 |
| 2026-04 | 2026 |  | +21.5 | +23.9 | -2.4 | correct | -0.1 |
| 2026-05 | 2026 |  | +20.1 | +32.0 | -11.9 | MISS | -6.9 |

**Summary (Instrument A, 2023-01→2026-05):** mean signed **+0.36 bp** (selection-asterisked, see header) · MAE 7.97 · median 7.25 · 10–90 band [-11.9, +12.7] bp · boundary hit-rate ex-COIN-FLIP 39% (11/28; 12 coin-flip) · skipped 1

**Side-by-side vs pre-reversal** (H9c drifts → freeze null): mean signed **+3.28 → +0.36 bp**
(the drift reversal removed the over-correction, restoring the unbiased monitor). MAE ~8 bp
unchanged (the drifts affected level, not dispersion). Per-era note: window is entirely
2023+; no pre-2023 rows here (the trailing-5y pre/post split lives in `pce_bridge_acceptance.md`).

### d. PRISTINE tier — forward prints (post-2026-07-21)

| print | ref month | released | instrument | dev (bp) |
|---|---|---|---|---|
| _(none yet — first genuinely-forward print will populate this)_ | | | | |

---
*Selection asterisk:* Instrument A's 2023+ numbers are QUASI-OOS — the residue respec and H9c
reversal were adjudicated on this window. Only the PRISTINE tier, once populated by forward
prints, can confirm the monitor's unbiasedness out-of-sample. No tier is blended into another's
summary stat.

---
## vs the market's number (Session 8)

Instrument A's story is **speed**: its core-PCE call is made on **CPI-day, ~16 days before the
SPF/consensus survey close**. That head start cannot be scored yet — a per-print consensus panel is
gap-first (auto-backfill 403-blocked; manual curation only). SPF is ingested as a separate quarterly
trajectory benchmark; Cleveland Fed as a per-print external number. See `benchmark_evaluation_1.md`.
No tier blended: rounded (market) and unrounded (our-call) metrics are kept in separate columns.
