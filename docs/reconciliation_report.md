# Reconciliation report (Session 2B, Gate 2)

Official-side MoM read via `timebase.asof_mom_for_ref` (first-release, within-vintage) — never latest-vintage. Shutdown/series-start months are counted in `skipped`, never imputed. `optimistic` marks stats from `revised_latest_only` proxies (their history was restated, so real-time tracking is necessarily flattered here).

## Table (sorted by CPI weight × R²)

`pre_floor` = official reference months excluded for being below the series' vintage_floor (ALFRED bulk-archived, restated-as-first). `skip` = shutdown-gap / series-start / not-yet-released. Both excluded from the regression, never imputed.

| pair | CPI wt | n | skip | pre_floor | beta | R² | quality | optimistic |
|---|--:|--:|--:|--:|--:|--:|---|:--:|
| EIA gasoline vs CPI Gasoline (SETB01) | 2.90 | 184 | 1 | 246 | +0.810 | 0.746 | stable |  |
| ZORI vs CPI Shelter (SAH1) | 35.62 | 135 | 2 | 0 | +0.089 | 0.031 | unstable | ✓ |
| ZORI vs CPI OER (SEHC01) | 25.23 | 135 | 2 | 0 | +0.045 | 0.010 | unstable | ✓ |
| ZORI vs CPI Rent of primary residence | 7.84 | 135 | 2 | 0 | +0.042 | 0.007 | unstable | ✓ |
| EIA heating-oil spot vs CPI Energy | 0.08 | 354 | 3 | 124 | +0.188 | 0.330 | stable |  |
| NADAC vs CPI Medical-care commodities | 0.97 | 58 | 2 | 0 | -0.009 | 0.012 | unstable |  |
| Manheim vs CPI Used cars (SETA02) | 2.76 | 10 | 0 | 0 | — | — | insufficient_overlap |  |
| Atlanta Fed wage tracker | 0.00 | 353 | 0 | 0 | — | — | monitor | ✓ |
| Indeed wage tracker | 0.00 | 90 | 0 | 0 | — | — | monitor | ✓ |

**Optimism-flagged pairs (proxy vintage unavailable): 5**

## UNSTABLE pairs — one-line diagnoses

- **ZORI vs CPI Shelter (SAH1)** (R²=0.031): beta sign flips across windows (-0.47..+0.89); R² collapses in stress window(s) ['2018-02-01..2021-01-01', '2020-02-01..2023-01-01', '2022-02-01..2025-01-01']. coarser: shelter incl OER + lodging
- **ZORI vs CPI OER (SEHC01)** (R²=0.010): beta sign flips across windows (-0.36..+0.64); R² collapses in stress window(s) ['2018-02-01..2021-01-01', '2020-02-01..2023-01-01', '2022-02-01..2025-01-01']. OER direct (Session-2B add, 25% weight). H2 again: R²~0, unstable — market rent leads all-tenant OER ~1yr; ALFRED first-release from ~2011.
- **ZORI vs CPI Rent of primary residence** (R²=0.007): beta sign flips across windows (-0.21..+0.78); R² collapses in stress window(s) ['2018-02-01..2021-01-01', '2019-02-01..2022-01-01', '2020-02-01..2023-01-01']. SA vs SA; primary shelter pair. ZORI is a market-rent index; CPI rent is a smoothed all-tenant series lagging market by ~1yr (research plan H2).
- **NADAC vs CPI Medical-care commodities** (R²=0.012): beta sign flips across windows (-0.01..+0.03); R² collapses in stress window(s) ['2021-02-01..2024-01-01', '2022-02-01..2025-01-01']. PLACEHOLDER index, 1-year bounded (2024-25) -> too short for the rolling harness (insufficient_overlap expected). Official side = SAM1 (medical-care commodities) since drugs stratum SEMF01 has no ALFRED vintages. 3A: full history + proper weighted matched-model + drug-specific official.

## Monitors (not regressed)

- **Atlanta Fed wage tracker**:  | MONITOR: wage-growth rate, not regressed as a price proxy
- **Indeed wage tracker**:  | MONITOR: wage-growth rate, not regressed as a price proxy
