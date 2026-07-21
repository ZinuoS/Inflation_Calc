# Seasonal-adjustment & vintage floors on achievable accuracy

Two irreducible error sources bound how accurate a component nowcast can be, before any
model is fit. Both are measured, not assumed. §1–§3 are **motivation**; §4 is the
**operative floor** the live nowcast is actually bounded by, after the Checkpoint-2 reroute.

## 1. Vintage leakage — why latest-vintage backtests overstate skill

A backtest that reads *revised* (latest-vintage) values instead of *first-release* values
is not measuring real-time skill; it is reading the future. Two exhibits from the
Session-2A firewall work (`tests/test_vintage_mom.py`, checkpoint log s2a):

- **PCE re-referencing: 711 bp.** At the 2023 BEA comprehensive update, naive
  cross-vintage MoM for one reference month is **−6.97%** versus the true within-vintage
  first-release **+0.145%** — 711 bp of pure look-ahead a latest-vintage backtest would
  "predict".
- **CPI February seasonal restatement: 3.5 bp, recurring.** Each February BLS restates the
  SA history with revised seasonal factors; a latest-vintage backtest gets a systematic
  ~3.5 bp free edge that recurs every year in the direction of the revision.

The firewall (`timebase.py`, `first_release_mom`, `vintage_floor`) removes both by
construction. This is why the admission table's numbers are first-release only.

## 2. SA replication floor — our X-13 vs BLS published SA (MOTIVATION — retired as the gate)

BLS seasonally adjusts each series with a per-series-tuned X-13ARIMA-SEATS spec
(outliers, regARIMA regressors, seasonal filters chosen per series). We applied a
**default** X-13 (`automdl` + default `x11`) via `src/nowcast/seasonal.py` and measured the
gap to BLS published SA, MoM MAE in bp over the trailing 8 years (`seasonal.sa_replication_mae`):

| stratum | code | n | SA-replication MAE (bp/MoM) | corr |
|---|---|--:|--:|--:|
| Apparel | SAA | 86 | 16.6 | 0.966 |
| Gasoline | SETB01 | 95 | 72.9 | 0.986 |
| Used cars | SETA02 | 95 | 83.1 | 0.868 |
| Airline fares | SETG01 | 86 | 95.4 | 0.959 |

Every stratum exceeds the old 3 bp target by 5×–30×. Verified genuine, not a scaling bug:
our SA tracks BLS closely in level and direction (gasoline our −9.27% vs BLS −9.69%;
apparel our +0.29% vs BLS +0.33%) with 0.87–0.99 correlation. The residual **scales with
each stratum's MoM volatility** — a small relative SA-method difference becomes tens of bp
absolute on volatile series.

**Why this table is motivation, not the floor.** It measures *our X-13 vs BLS's X-13* — a
method-replication residual. But the live nowcast does **not** re-estimate SA. It forecasts
in **NSA space** (NSA CPI is never revised — verified: 0 changed reference values across
154–183 ALFRED vintages for gasoline/used-cars/airfares) and converts to SA with **BLS's
own factors**. So our-X13-vs-BLS never enters the live path. The operative floor is not this
residual; it is **factor-extrapolation error** (§4). `seasonal.py`'s X-13 is retained only
for de-noising alternative proxies where no official factor exists.

## 3. The reroute (Checkpoint-2 decision)

Neither tune our X-13 nor accept the volatility-scaled §2 floor. Instead:

- **NSA is final at first release** (never revised) → the NSA side needs no vintage.
- **BLS factors are predetermined within a year** — projected in the February revision and
  applied mechanically thereafter. So the only thing unknown at forecast time is *which
  factor BLS will have applied to the target month*, and how well we can anticipate it.

`implied_factor(item, month) = NSA / SA`. `factor_asof(item, target, forecast_time)` is the
factor knowable at forecast time. `src/nowcast/factors.py` implements both;
`factor_extrapolation_error` is the operative floor.

## 4. Operative floor — factor-extrapolation error (THE GATE)

For each month in the trailing 8 years: `SA_est = NSA / factor_asof`, then its MoM vs the
realized **first-release** SA MoM; MAE in bp, split **ex-February** vs **February** (where
the annual factor revision lands — the §1 3.5 bp headline exhibit, now resolved per
stratum). `factor_asof` here is the **carry-forward** factor: the latest same-calendar-month
implied factor from the then-available vintage (last year's factor for that month).

| stratum | code | n (ex-Feb) | **MAE ex-Feb (bp/MoM)** | n (Feb) | MAE Feb (bp) | MAE all (bp) |
|---|---|--:|--:|--:|--:|--:|
| Apparel | SAA | 85 | **9.19** ✅ | 8 | 17.97 | 9.95 |
| Gasoline | SETB01 | 88 | **18.16** ❌ | 8 | 119.53 | 26.61 |
| Used cars & trucks | SETA02 | 88 | **16.85** ❌ | 8 | 48.93 | 19.52 |
| Airline fares | SETG01 | 85 | **14.45** ❌ | 8 | 115.44 | 23.14 |

**Acceptance check (new gate): MAE ex-February < 10 bp/MoM per stratum.** Apparel passes
(9.19). Gasoline, used cars, and airfares **fail** (14–18 bp). Per the reroute's pre-set
rule, three strata exceeding even this floor is **a real finding → HALT**.

Two things this table establishes:

1. **The reroute more than halves the floor.** Ex-February, gasoline drops 72.9 → 18.2 bp,
   airfares 95.4 → 14.5 bp vs the §2 method residual. Forecasting in NSA space and applying
   BLS's factor is strictly better than replicating BLS's SA ourselves.
2. **February concentrates the residual.** The §1 headline "3.5 bp February" exhibit
   generalizes per stratum to **18–120 bp** in February reference months — the annual factor
   revision, isolated. Ex-February is 9–18 bp.

### Why the ex-February residual was not irreducible — the carry-forward penalty

The 9–18 bp ex-February floor is an artifact of `factor_asof` using **carry-forward** (last
year's same-month factor) as a proxy for BLS's predetermined factor. Measured directly, the
factor *itself* drifts year-over-year by **25–122 bp ex-February** (apparel 25, used cars
59, gasoline 101, airfares 123); the MoM impact is smaller (9–18 bp) only because adjacent
months' drifts partly cancel in the factor ratio. But BLS **publishes** its projected factors
for the year ahead and applies them mechanically at first release, so the realized
first-release factor for month M *is* BLS's published projected factor for M. Carry-forward is
therefore an **upper bound**.

## 5. RESOLUTION — harvest BLS's published projected factors (option a, implemented)

Decision at Checkpoint 3b: **(a)**. New pipeline `pipelines/bls_seasonal_factors/` harvests
the annual "Seasonal factors table, YYYY" XLSX (2021–2026 machine-readable; pre-2021 PDF-only
and robots-disallowed, so out of scope) into `bls_seasonal_factors`, keyed by
(series_id, reference_period) and stamped with `published_asof` = the January-YYYY CPI release
date (when the factors are introduced — the vintage key). `src/nowcast/factors.py`
`published_factor_asof` returns the projected factor for a month only if it was introduced
strictly before forecast_time; `factor_conversion_error` is the resulting floor.

**Validation (identity).** The harvested published factor equals `NSA / SA_firstrelease` to
**0.01 bp** across all tested months — i.e. it *is* the factor BLS applies at first release,
confirming we harvested the applied factor and not a hindsight-revised one (`test_factors.py`).

**Operative floor with harvested factors** — SA-conversion MoM MAE (bp), trailing 8y,
forecast_time = each month's CPI release date:

| stratum | code | clean months (Mar–Dec) | n | boundary (Jan/Feb seam) | n |
|---|---|--:|--:|--:|--:|
| Gasoline | SETB01 | **0.02** ✅ | 54 | 130.4 | 10 |
| Used cars & trucks | SETA02 | **0.02** ✅ | 54 | 44.4 | 10 |
| Airline fares | SETG01 | **0.02** ✅ | 51 | 130.3 | 10 |

**Ten of twelve months per year (March–December) have a ~0.02 bp SA-conversion floor** — a
~750× cut from the carry-forward 14–18 bp, and three orders of magnitude under the 10 bp gate.
The reroute + harvest **essentially eliminates the SA floor** for directly-adjusted strata.

**The residual is a two-month annual seam, and it is irreducible in real time.** January's
year-Y factor is introduced *with January's own release*, so a forecaster nowcasting January
holds only the prior year's factor; February then inherits January's off-base level. This is
the §1 "February seasonal restatement" exhibit, now located exactly and quantified per
stratum (44–130 bp). It is a **calendar fact, not a model floor** — carry January/February as
a known, bounded, once-a-year event (wider intervals, or a small same-month factor model for
those two months only).

### Coverage notes

- **Apparel (SAA), food-at-home (SAF11), and other aggregates are *indirectly* adjusted** —
  BLS builds their SA by aggregating directly-adjusted components, so they have no single
  published factor (the factor file shows "–"). `published_factor_asof` returns None for them;
  their SA comes from component aggregation (Task 5). Apparel's carry-forward 9.19 bp stands
  as its interim floor until the component-aggregation path is built.
- **Headline/core all-items** rows remain deferred: no all-items NSA index is loaded
  (`CUUR0000SA0`/`SA0L1E` absent from `official_current`); the all-items NSA is a **derived**
  quantity, reconstructed by aggregation in Task 5, after which its conversion floor can be
  reported against `CPIAUCSL`/`CPILFESL`. A coverage note, not a bug.
