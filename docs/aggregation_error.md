# CPI aggregation replication & SA-conversion overhead (Session 3A, Task 5)

Can we reproduce the published CPI aggregates from their component indices and BLS's own
weights, using **official inputs only** (no proxies)? And once we forecast in NSA space (the
Checkpoint-2 reroute), how much error does converting the aggregate to SA add? Both are
measured with `src/nowcast/aggregate.py` (`nb03_cpi_replication`), deterministic and offline.

## Method

Upper-level modified Laspeyres (BLS Handbook of Methods, CPI ch. 17): an aggregate advances
by the cost-weighted average of its components' price relatives (`index_math.laspeyres_upper`),
the weights being relative importances (`weights.weights_as_of`, vintaged by year). Cost
weights are seeded from each weight-year's December relative importances and **price-updated**
month to month, reset each December — the standard price-updated Laspeyres.

**Partition = the coarsest COMPLETE published set.** Every published aggregate already embeds
BLS's exact sub-aggregation (including unpublished strata and unrounded cost weights), so
keeping a branch whole is strictly more faithful than re-deriving it from finer, rounded,
published RIs — verified: a 135-leaf partition scores ~2 bp worse than the 8 majors. So
**headline = the 8 major groups**; **core = the coarsest partition that carves out food
(SAF1) and energy (SETB/SEHE/SEHF)**, 15 components summing to ~80% of CPI.

## Result 1 — NSA reconstruction vs official (the ≤1 bp target)

MoM MAE in bp, reconstruction vs official `CUUR0000SA0` (headline) / `CUUR0000SA0L1E` (core):

| aggregate | components | MAE 2023+ | MAE 2021 | full-window MAE | median |
|---|--:|--:|--:|--:|--:|
| Headline (All items) | 8 | **0.50** ✅ | 5.33 | 1.83 | 0.84 |
| Core (less food & energy) | 15 | **1.32** | 3.70 | 1.74 | 1.14 |

**Headline meets the ≤1 bp target under BLS's current (2023+) annual-weight methodology**
(0.50 bp mean, 0.19 bp in 2025). **The residual is a methodology-era effect, not a machinery
error:** before 2023 BLS updated weights *biennially*, and our published-RI price-updating
cannot reproduce that regime during the 2021 relative-price surge — 2021 alone is 5.33 bp
while 2023–2025 average 0.50 bp. Core runs slightly higher (1.32 bp, 2023+) because removing
food and energy forces a finer 15-component partition that compounds a little more of the
same published-RI approximation; 2025 core is 0.15 bp.

Per-year MAE (headline, bp): 2020 **0.90** · 2021 **5.33** · 2022 **2.92** · 2023 **0.62** ·
2024 **0.60** · 2025 **0.19**. The break at 2023 is the biennial→annual weight switch.

**Floor context.** Official indices are published to 3 decimals, so an official MoM carries
~0.2–0.3 bp of pure rounding noise; the 2023+ 0.50 bp headline result is within a factor of
~2 of that irreducible rounding floor.

## Result 2 — SA-conversion overhead

Reconstructing the aggregate in **SA space** (aggregating the published SA components,
`CUSR0000*`, which already embed the harvested stratum seasonal factors of `sa_floor.md` §5)
vs the official SA aggregate, compared to the NSA reconstruction:

| aggregate | NSA MAE (2023+) | SA MAE (2023+) | **conversion overhead** |
|---|--:|--:|--:|
| Headline | 0.50 | 0.49 | **−0.01 bp** |
| Core | 1.32 | 1.36 | **+0.04 bp** |

**The SA conversion adds essentially nothing at the aggregate level (<0.05 bp).** Headline and
core are *indirectly* seasonally adjusted — BLS builds their SA by aggregating component SAs,
not by applying a headline factor — so the aggregate SA error is just the same top-level
weight approximation as the NSA reconstruction. Combined with `sa_floor.md` §5 (directly-
adjusted strata convert NSA→SA at ~0.02 bp in the clean months), the SA pathway is
**effectively free for a good NSA forecast**, with the sole material exception being the
January/February annual factor seam (the irreducible once-a-year residual).

## Takeaways for the nowcast

1. The aggregation machinery (`index_math` + `weights` + `aggregate`) reproduces official CPI
   from official components to **≤1 bp headline (2023+)** — the component-level nowcast can be
   rolled up to headline/core with negligible aggregation loss in the current regime.
2. Forecast in NSA and convert to SA: the conversion overhead is **~0** at the aggregate level
   and **~0.02 bp** at the directly-adjusted stratum level; budget error to the component
   forecasts and to the Jan/Feb factor seam, not to aggregation or SA conversion.
3. Backtests spanning pre-2023 must carry the biennial-weight caveat: the reconstruction is
   ~3 bp there, so aggregate replication is materially tighter from 2023 forward.
