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
| Manheim vs CPI Used cars (SETA02) | 2.76 | 177 | 0 | 169 | +0.103 | 0.015 | unstable |  |
| EIA heating-oil spot vs CPI Energy | 0.08 | 354 | 3 | 124 | +0.188 | 0.330 | stable |  |
| NADAC vs CPI Medical-care commodities | 0.97 | 58 | 2 | 0 | -0.009 | 0.012 | unstable |  |
| Atlanta Fed wage tracker | 0.00 | 353 | 0 | 0 | — | — | monitor | ✓ |
| Indeed wage tracker | 0.00 | 90 | 0 | 0 | — | — | monitor | ✓ |
| TSA throughput (airfare demand) | 0.00 | 6 | 0 | 0 | — | — | monitor |  |

**Optimism-flagged pairs (proxy vintage unavailable): 5**

## UNSTABLE pairs — one-line diagnoses

- **ZORI vs CPI Shelter (SAH1)** (R²=0.031): beta sign flips across windows (-0.47..+0.89); R² collapses in stress window(s) ['2018-02-01..2021-01-01', '2020-02-01..2023-01-01', '2022-02-01..2025-01-01']. coarser: shelter incl OER + lodging
- **ZORI vs CPI OER (SEHC01)** (R²=0.010): beta sign flips across windows (-0.36..+0.64); R² collapses in stress window(s) ['2018-02-01..2021-01-01', '2020-02-01..2023-01-01', '2022-02-01..2025-01-01']. OER direct (Session-2B add, 25% weight). H2 again: R²~0, unstable — market rent leads all-tenant OER ~1yr; ALFRED first-release from ~2011.
- **ZORI vs CPI Rent of primary residence** (R²=0.007): beta sign flips across windows (-0.21..+0.78); R² collapses in stress window(s) ['2018-02-01..2021-01-01', '2019-02-01..2022-01-01', '2020-02-01..2023-01-01']. SA vs SA; primary shelter pair. ZORI is a market-rent index; CPI rent is a smoothed all-tenant series lagging market by ~1yr (research plan H2).
- **Manheim vs CPI Used cars (SETA02)** (R²=0.015): beta sign flips across windows (-0.42..+0.29); R² collapses in stress window(s) ['2018-03-01..2021-02-01', '2019-03-01..2022-02-01', '2020-03-01..2023-02-01', '2021-03-01..2024-02-01', '2022-03-01..2025-02-01']. H1 feedstock. Full 1997-2025 unrevised (Task 0b: 11-mo point-in-time == latest download exactly). Contemporaneous R²~0.02 UNSTABLE because Manheim wholesale LEADS CPI used-car retail — peak R²=0.35 at a 2-month lead (Session-4 H1, not a next-print contemporaneous feature).
- **NADAC vs CPI Medical-care commodities** (R²=0.012): beta sign flips across windows (-0.01..+0.03); R² collapses in stress window(s) ['2021-02-01..2024-01-01', '2022-02-01..2025-01-01']. PLACEHOLDER index, 1-year bounded (2024-25) -> too short for the rolling harness (insufficient_overlap expected). Official side = SAM1 (medical-care commodities) since drugs stratum SEMF01 has no ALFRED vintages. 3A: full history + proper weighted matched-model + drug-specific official.

## Monitors (not regressed)

- **Atlanta Fed wage tracker**:  | MONITOR: wage-growth rate, not regressed as a price proxy
- **Indeed wage tracker**:  | MONITOR: wage-growth rate, not regressed as a price proxy
- **TSA throughput (airfare demand)**: demand monitor for airfares, not a price proxy; ~6mo | MONITOR: wage-growth rate, not regressed as a price proxy

---

# Task 4 (Session 3A) — NSA-vs-NSA reconciliation reruns

The Session-2B pairs above regressed **NSA proxies on the SA official** stratum — a
seasonality mismatch that capped R² and was flagged in each `note`. The Checkpoint-2 reroute
forecasts in NSA space, so the operative pairing is NSA-proxy vs **NSA-official**
(`official_current`, unrevised — leakage-safe only because the NSA index is never revised;
`reconcile.official_nsa_mom` asserts CUUR-only). Below, old vs new side by side.

## Gasoline — EIA retail vs CPI gasoline

| pairing | official series | n | beta | R² | quality |
|---|---|--:|--:|--:|---|
| OLD (Session 2B) | SA `CUSR0000SETB01` | 184 | +0.810 | **0.746** | stable |
| NEW (Task 4) | NSA `CUUR0000SETB01` | 430 | +0.965 | **0.978** | stable |

NSA-vs-NSA does two things at once: (1) it removes the SA-vs-NSA seasonality mismatch, and
(2) it drops the ~2011 ALFRED vintage floor (NSA is unrevised, so `official_current` needs no
vintage — the overlap more than doubles, 184 → 430 months back to ~1990). Beta rises to a
**near-unit retail→CPI pass-through (0.965)**, R² to **0.978**, rolling betas stay in
0.79–1.01, and the stress-window R² is ~0.99 through COVID. **Gasoline is a strong
contemporaneous NSA feature** — the SA-bounded 0.746 was an artifact of the mismatch, not the
proxy's true tracking.

## Used cars — Manheim wholesale (lead scan)

| target | contemp R² (k0) | peak lead | peak R² | quality |
|---|--:|--:|--:|---|
| OLD: SA `CUSR0000SETA02` | 0.015 | 2 | **0.346** | stable_leading |
| NEW: NSA `CUUR0000SETA02` | 0.017 | 2 | **0.197** | stable_leading |

The **2-month wholesale→retail lead survives** NSA-vs-NSA (still `stable_leading`, peak at
lead-2), but its peak R² **falls** 0.346 → 0.197 — the opposite direction from gasoline. This
is a genuine asymmetry: for a **contemporaneous** pair (gasoline, lag 0) the two sides'
seasonality aligns and NSA-vs-NSA helps; for a **leading** pair, shifting the proxy 2 months
**misaligns** its seasonal component against the target's, adding noise. So Manheim's lead
signal is cleanest against the **deseasonalized/SA** used-car change. Operational consequence
for the NSA framework: use Manheim (lead-2) to predict the **non-seasonal** part of the
used-car MoM, then re-apply the harvested seasonal factor (§ sa_floor.md §5) — do not regress
it NSA-on-NSA. Both scans are reproducible from `reconcile.lead_scan` / `lead_scan_nsa`
(`test_reconcile.py`).

## Conditional builds (Keepa / USDA / BEA)

`.env` rechecked 2026-07-20: `KEEPA_API_KEY`, `USDA_AMS_API_KEY`, `BEA_API_KEY` all still
**absent** (only `FRED_API_KEY` present). keepa / usda_ams / bea_pce_detail remain **SKIPPED**
(folders + specs + STATUS notes stand); no builds this task.
