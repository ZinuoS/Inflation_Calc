# Performance report — Stage 1 (replication & infrastructure)

Written for a reader who was in none of the build sessions. Stage 1 covers everything through
Session 3B: methodology **replication** (can we reproduce official CPI/PPI/PCE from components?)
and the **leakage-firewall infrastructure**. It does **not** cover forecasting — no pre-print
CPI/PPI model exists yet (Session 4). Numbers below are stated without spin in either direction;
where a target was missed it says so.

---

## 1. Replication accuracy

### CPI aggregation — at the index-rounding floor
Reconstructing published CPI from its official component indices + BLS relative-importance
weights (`src/nowcast/aggregate.py`, price-updated Laspeyres over the coarsest complete
published partition), MoM MAE vs the official first-release print:

| aggregate | MAE (2023+ current-method) | full 5y | 2026 OOS (tariff era) |
|---|--:|--:|--:|
| **Headline** (All items) | **0.50 bp** | 1.83 | NSA **0.02**, SA **0.39** |
| **Core** (less food/energy) | **1.32 bp** | 1.74 | NSA **0.02**, SA **0.71** |

- **Headline meets ≤1 bp** under BLS's current (2023+) annual-weight methodology; NSA
  reconstruction sits at ~0.02 bp — within ~2× the irreducible 0.2–0.3 bp index-rounding floor.
- **Core misses the ≤1 bp target at 1.32 bp (2023+).** Materiality: core must carve out
  food/energy, forcing a finer 15-component partition that compounds slightly more of the
  published-RI approximation; it is ~0.3 bp over target, not a regime issue. Both aggregates
  degrade pre-2023 (headline 5.3 bp in 2021) because BLS used *biennial* weights then, which
  our published-RI price-updating cannot reproduce during the 2021 relative-price surge — a
  methodology-era artifact, not a machinery error, and it is documented as a backtest caveat.
- The **2026 out-of-sample** check (tariff regime, stale 2025 weights) reproduces prints to
  ~0.02–0.7 bp — the machinery generalizes.

### Seasonal-adjustment pathway — the reroute that retired a 17–95 bp floor
The first SA approach (our own default X-13 vs BLS's per-series-tuned SA) left a
**method-residual of 16.6–95.4 bp/MoM** across apparel/gasoline/used-cars/airfares — a
volatility-scaled floor that would have swamped any component signal. This was **retired**, not
accepted: the nowcast forecasts in **NSA space** (NSA CPI is never revised — verified 0 changed
values across 154–183 ALFRED vintages) and converts to SA using **BLS's own harvested projected
seasonal factors** (`src/nowcast/factors.py`, `pipelines/bls_seasonal_factors`). Result: the
harvested factor equals the applied first-release factor to **0.01 bp**, and the SA-conversion
overhead is **~0.02 bp** at the stratum level (clean months) and **~0 bp** at the aggregate
level (−0.01 headline / +0.04 core). The sole material SA residual is the **January/February
annual factor seam** — a bounded, once-a-year calendar event, carried explicitly.

## 2. CPI/PPI → core-PCE bridge

**Valid gate: BLOCKED.** The bridge needs BEA underlying-detail weights (Table 2.4.5U), which
require a BEA API key that is not yet available (and BEA detail is not publicly downloadable —
API key-gated, flatfiles 403, iTable JS-gated). The valid gate could not be run.

**Degraded-input gate (recorded outcome, run on CPI-relative-importance PROXY weights):**

| tier | threshold | 5-year | 2026 holdout |
|---|---|--:|--:|
| Tier 1 MAE | ≤ 2.0 bp | **12.2 bp** ❌ | **11.4 bp** ❌ |
| Tier 2 correct side | ≥ 85% | **27.5%** ❌ | 0/5 ❌ |

Diagnosis (`docs/pce_bridge_acceptance.md`): the proxy weights over-weight **shelter to 46% of
core** (PCE ~15–18%) and, summing to only 71.6%, **near-zero-weight the PPI-priced healthcare**
(~22% of core PCE) and imputed financial/NPISH — so the bridge is structurally blind to ~30% of
core PCE. The error **flips sign by regime** (over-predicts the 2020–22 shelter surge,
under-predicts the 2026 tariff regime), which is why no calibration offset was added — a
constant cannot fix a sign-flipping error.

**Pre-registered expectation (unchanged, untested):** true 2.4.5U weights should collapse Tier-1
MAE from ~12 bp to low single digits (shelter re-weight + healthcare activation). A genuine
failure *with* true weights would be real K1 (kill-decision) evidence. This side-by-side table
will gain a "valid" column when the BEA key lands; today it has only the degraded column.

## 3. Signal inventory (component-level, first-release)

| signal | role | evidence | status |
|---|---|---|---|
| **Gasoline** EIA-retail vs CPI SETB01 | contemporaneous | **R² = 0.978**, β = 0.965 (NSA-vs-NSA, n=430, stress-R² ~0.99) | **admitted** |
| **Manheim** wholesale vs CPI used cars | leading (H1) | `stable_leading`, peak **R² = 0.35 @ lag-2**; contemporaneous ~0.02 | admitted as **lag-2 feature only** |
| **Shelter** (ZORI vs rent/OER, H2) | — | R² ~0.01, β sign-flips; **confirmed both statistically and calendrically** (ZORI for month M lands ~T+14, after the CPI print) | **excluded** as next-print; leading-only |
| NADAC drugs, other proxies | — | insufficient overlap / monitor | pending |

Reconciliation ledger: 2 stable, 5 unstable, 3 monitor; **5 optimism-flagged** (revised-latest-
only proxies). Nothing is silently dropped — exclusions are flagged with a diagnosis. (The
gasoline 0.978 supersedes the old SA-bounded 0.746; see `docs/reconciliation_report.md`.)

## 4. Infrastructure guarantees

- **Dual leakage firewall.** Official side: `timebase` + within-vintage `first_release_mom` +
  `vintage_floor`. Proxy side (new this session): `proxy_timebase.proxy_asof` with per-source,
  cited publication rules — **standing rule: Session-4 features must read proxies through
  `proxy_asof`.** Adversarial tests on both sides treat a leak as a build failure.
- **Why the firewall matters, quantified:** a latest-vintage backtest would "predict" a **711 bp**
  PCE re-referencing jump and a recurring **~3.5 bp** CPI February seasonal restatement — both
  removed by construction.
- **Availability calendar** (`docs/availability_calendar.md`): per-print T-minus arrival timeline
  with a "last useful update" line — e.g. the bridge's PCE call is knowable on **CPI-day, ~15
  days before** the official PCE print.

## 5. NOT YET DONE (stated plainly — this section must not shrink)

- **No pre-print CPI/PPI forecast exists.** Everything above is *replication given the prints*,
  not prediction. The component forecasting models and their pre-registered evaluation are
  **Session 4, unstarted.**
- **No forward data collectors** (Session 5) — today's inputs are historical pulls.
- **No live daily tracking harness** (Session 6).
- **Consensus-history decision open** — surprise-vs-consensus targets need a consensus series
  not yet sourced.
- **Conditionals still skipped for lack of credentials:** BEA 2.4.5U/2.4.4U (blocks the valid
  PCE gate + verified attribution), Keepa daily consumer-goods layer, USDA food-at-home.
- **Core CPI replication is ~0.3 bp over its ≤1 bp target**; headline meets it.

**Bottom line:** replication is at the rounding floor and the firewall is in place; **predictive
edge is untested by design until Session 4's pre-registered evaluation.**
