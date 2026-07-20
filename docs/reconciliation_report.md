# Reconciliation report (Session 2B, Gate 2)

Official-side MoM read via `timebase.asof_mom_for_ref` (first-release, within-vintage) — never latest-vintage. Shutdown/series-start months are counted in `skipped`, never imputed. `optimistic` marks stats from `revised_latest_only` proxies (their history was restated, so real-time tracking is necessarily flattered here).

## Table (sorted by CPI weight × R²)

| pair | CPI wt | n | skip | beta | R² | quality | optimistic |
|---|--:|--:|--:|--:|--:|---|:--:|
| EIA gasoline vs CPI Energy | 2.90 | 428 | 3 | +0.438 | 0.758 | stable |  |
| ZORI vs CPI Shelter (SAH1) | 35.62 | 135 | 2 | +0.089 | 0.031 | unstable | ✓ |
| ZORI vs CPI Rent of primary residence | 7.84 | 135 | 2 | +0.042 | 0.007 | unstable | ✓ |
| EIA heating-oil spot vs CPI Energy | 0.08 | 478 | 3 | +0.153 | 0.266 | unstable |  |
| Atlanta Fed wage tracker | 0.00 | 353 | 0 | — | — | monitor | ✓ |
| Indeed wage tracker | 0.00 | 90 | 0 | — | — | monitor | ✓ |

**Optimism-flagged pairs (proxy vintage unavailable): 4**

## UNSTABLE pairs — one-line diagnoses

- **ZORI vs CPI Shelter (SAH1)** (R²=0.031): beta sign flips across windows (-0.47..+0.89); R² collapses in stress window(s) ['2018-02-01..2021-01-01', '2020-02-01..2023-01-01', '2022-02-01..2025-01-01']. coarser: shelter incl OER + lodging
- **ZORI vs CPI Rent of primary residence** (R²=0.007): beta sign flips across windows (-0.21..+0.78); R² collapses in stress window(s) ['2018-02-01..2021-01-01', '2019-02-01..2022-01-01', '2020-02-01..2023-01-01']. SA vs SA; primary shelter pair. ZORI is a market-rent index; CPI rent is a smoothed all-tenant series lagging market by ~1yr (research plan H2).
- **EIA heating-oil spot vs CPI Energy** (R²=0.266): beta sign flips across windows (-0.02..+0.38). VERY COARSE: wholesale spot vs energy aggregate

## Monitors (not regressed)

- **Atlanta Fed wage tracker**:  | MONITOR: wage-growth rate, not regressed as a price proxy
- **Indeed wage tracker**:  | MONITOR: wage-growth rate, not regressed as a price proxy
