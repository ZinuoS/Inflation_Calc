# Backtest export — our call vs the actual release vs consensus (pp)

**`data/benchmarks/backtest_vs_consensus.csv`** — 216 rows, one per (instrument, reference month).
Regenerate with:

```
python -c "from nowcast import backtest_export as X; X.write_csv()"
```

All values in **percentage points (pp)**, the release convention (1 pp = 100 bp; one published
increment = 0.1 pp). Quoted to **4 dp** (0.0001 pp = 0.01 bp), and **internally self-consistent**:
every error column is computed from the quantised values that appear in the file, so recomputing
`our_err_pp = our_call_pp − actual_pp` from the CSV reproduces the printed figure exactly.

## Columns

| column | meaning |
|---|---|
| `instrument` | `cpi_headline`, `cpi_core`, `pce_core` |
| `reference_month`, `release_date` | from `release_calendar` |
| `our_call_pp` | our frozen call at the T-3 freeze (CPI) / CPI-day (PCE) |
| `our_call_basis` | **`sa_converted_from_nsa`** (CPI) or **`native_sa`** (PCE) — see basis note |
| `actual_pp` | published first release, **unrounded** SA MoM |
| `actual_rounded_pp` | the published tenth (what the market trades) |
| `consensus_pp` | press-consensus median, **already rounded**; blank = gap, never imputed |
| `consensus_source_url`, `consensus_article_date` | citation for that consensus cell |
| `cleveland_pp` | Cleveland Fed nowcast, final pre-release value |
| `our_err_pp`, `consensus_err_pp`, `cleveland_err_pp` | call − actual |
| `divergence_pp` | our call − consensus (the PR-1 input) |
| `boundary_month` | actual within 0.015 pp of a rounding boundary (COIN-FLIP) |

## Basis note — the honest caveat

CPI consensus is quoted **SA**; our CPI instrument is **NSA-native**. Our call is therefore converted
to the SA basis with the leakage-safe prior-year implied factor (validated ~0.025 pp headline /
~0.019 pp core). **That conversion is a handicap on us and is never adjusted away** — every row is
labelled. PCE Instrument A is natively SA, so no conversion applies.

Consensus is a median of **rounded** forecasts, so `consensus_err_pp` compares a rounded number to an
unrounded actual. Rounded and unrounded quantities are kept in separate columns and are never averaged
into a single statistic.

**No YoY column.** Hard rule 8 bars YoY as a target or metric (overlapping 12-month windows
autocorrelate the error series and inflate apparent skill). YoY appears only as derived release
context in `docs/pce_status_report.md`.

## Head-to-head, consensus months only (the only fair cut)

| instrument | n | our MAE (pp) | consensus MAE (pp) | boundary months |
|---|--:|--:|--:|--:|
| **cpi_headline** | 30 | **0.0727** | 0.0733 | 9 |
| cpi_core | 27 | 0.0853 | **0.0529** | 12 |
| pce_core | 9 | 0.0770 | **0.0367** | 3 |

Consistent with the Session-9 verdicts: **parity on headline** (0.0727 vs 0.0733 pp — a 0.0004 pp gap,
i.e. a tie), and **consensus ahead on core and PCE**. Consensus closes *after* our freeze and embeds
our own admitted signals, so this is the expected direction; the pre-registered PR-3 null holds.
Coverage is 66 of 216 rows — the rest are honest consensus gaps (2019–2022 predates the curated panel;
contaminated months were dropped rather than guessed).
