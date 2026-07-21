# Session 3A checkpoint log — index math + seasonal adjustment

## TASK 0 — carry-questions · CHECKPOINT 0

### 0a — C1–C3 conditional builds
`USDA_AMS_API_KEY`, `BEA_API_KEY`, `KEEPA_API_KEY` all still **ABSENT** from `.env`.
usda_ams / bea_pce_detail / keepa remain **SKIPPED** (folders + specs + STATUS notes
stand). No builds this session; their placeholder indices stay out of Task 4 scope
until a key lands.

### 0b — Manheim restatement verification → UNREVISED, historical ingested
Compared the point-in-time archive (11 dated files, Jan–Nov 2025, each file's newest row =
that month's first release) against the same months in the latest full download:
**all 11 months matched EXACTLY (diff 0.0000).** Methodology confirms the only historical
"recalculation" was the one-time 1995→1997 rebasing; "revised" = full-month superseding the
preliminary mid-month, not restatement of published full-month values.

→ MUVVI full-month is **unrevised**. Ingested the full **1997–2025 (347 months)** history
as `vintage_status: unrevised`, superseding the 11 point-in-time rows (values identical).
Evidence + residual caveat (2025-only exact-match window; annual SA revision of pre-2025
history not positively excluded) cited in `pipelines/manheim/license_note.md`.

**H1 no longer overlap-starved.** Reconciliation Manheim vs SETA02 (used cars),
first-release: contemporaneous **n=177, R²=0.015, unstable, NOT optimism-flagged**. That
low contemporaneous R² is the honest LEAD structure, not a defect — a lead-correlation
sanity check confirms it (and validates the pipeline is not buggy):

| lead k (months) | n | corr | R² |
|---|--:|--:|--:|
| 0 (contemporaneous) | 177 | +0.122 | 0.015 |
| 1 | 177 | +0.394 | 0.155 |
| **2** | 177 | **+0.592** | **0.350** |
| 3 | 177 | +0.435 | 0.190 |

Manheim wholesale leads CPI used-car retail by ~2 months (peak R²=0.35) — real H1 signal,
to be exploited as a LEAD in Session 4, not admitted as a contemporaneous next-print feature
(same shape as ZORI/shelter H2, but a stronger, cleaner lead).

### Task-3 preflight (heads-up, not blocking now)
`x13as` binary is **NOT on PATH**. Task 3 (X-13ARIMA-SEATS) will STOP for its install per
the prompt; flagging now so it can be installed during review. macOS install step will be
given at Task 3.

56 tests green.

## TASK 2 — bls_cpi_weights + weights.py · DONE
Built the `bls_cpi_weights` naru pipeline (didn't exist; Session 1 only had the manual
pull). 6 RI vintages (2020–2025, 1616 rows), license note, golden parse test.
`weights.py`: as-of-date serving, vintaged (rent 7.862 in 2020 vs 7.84 in 2025), refuses
out-of-coverage (2019/2026 → OutOfWeightCoverage).

## TASK 3 — seasonal.py (X-13) · CHECKPOINT 2 (HALT: all strata > 3bp)

### x13as install (reproducible — conda-forge ships only a Linux binary, so built from source)
```
# 1. micromamba standalone (osx-arm64)
mkdir -p ~/.local/bin && curl -Ls https://micro.mamba.pm/api/micromamba/osx-arm64/latest \
  | tar -xj -C /tmp/mm bin/micromamba && mv /tmp/mm/bin/micromamba ~/.local/bin/micromamba
# 2. NOTE: conda-forge r-x13binary is noarch and ships a LINUX x86-64 binary -> unusable on
#    macOS arm64. So install a Fortran toolchain and build the native binary from source:
export MAMBA_ROOT_PREFIX=~/micromamba
~/.local/bin/micromamba create -y -p ~/micromamba-envs/x13 -c conda-forge gfortran make
# 3. Census TEXT (ascii) source — statsmodels needs the text variant (.out/.err/.d11),
#    NOT x13ashtml (html only). Build b62 with -fallow-argument-mismatch for gfortran 15:
curl -sL -o /tmp/x13text/src.tar.gz \
  https://www2.census.gov/software/x-13arima-seats/x13as/unix-linux/program-archives/x13as_asciisrc-v1-1-b62.tar.gz
# tar xzf; cd x13as_asciisrc-v1-1-b62
PATH=~/micromamba-envs/x13/bin:$PATH make -f makefile.gf FC=gfortran FFLAGS="-O2 -fallow-argument-mismatch -std=legacy"
gfortran -o x13as *.o     # makefile's $(LINKER) is empty -> link manually
mkdir -p ~/micromamba-envs/x13/x13bin && cp x13as ~/micromamba-envs/x13/x13bin/x13as
```
**X13PATH = `/Users/zinuoshi/micromamba-envs/x13/x13bin`** (native Mach-O arm64 text x13as).
Set explicitly in every run command. statsmodels smoke test passes.

### SA replication floor — HALT (all four strata > 3bp/MoM)
Our default X-13 SA (CUUR NSA) vs BLS published SA (CUSR), MoM MAE bp, trailing 8y:

| stratum | code | n | MAE bp | corr |
|---|---|--:|--:|--:|
| Apparel | SAA | 86 | 16.6 | 0.966 |
| Gasoline | SETB01 | 95 | 72.9 | 0.986 |
| Used cars | SETA02 | 95 | 83.1 | 0.868 |
| Airfares | SETG01 | 86 | 95.4 | 0.959 |

VERIFIED GENUINE (not a scale bug): our SA tracks BLS in level/direction/volatility with
0.87–0.99 corr; residual scales with each stratum's MoM volatility. All exceed 3bp → HALT
per the standing instruction. docs/sa_floor.md written (711bp/3.5bp vintage exhibits +
this floor table + per-stratum implication). Decision needed: tune per-series X-13 specs
to match BLS, or carry these strata as lead/monitor rather than contemporaneous SA-MoM.
Gasoline note for Task 4: recoverable headroom on its NSA/SA reconciliation gap is bounded
by this 72.9bp SA-method residual.

## TASK 3b — reroute: factors.py + factor-extrapolation floor · CHECKPOINT 3b (HALT: 3 of 4 > 10bp ex-Feb)

`src/nowcast/factors.py`: `implied_factor` (NSA/SA), `factor_asof` (carry-forward =
latest same-cal-month implied factor, vintage-safe via observations), `factor_extrapolation_error`.

**NSA-never-revised verified**: 0 changed reference values across 154–183 ALFRED vintages
(gasoline/used-cars/airfares) → NSA side needs no vintage; official_current = first release.

### Factor-extrapolation floor (carry-forward factor_asof), MoM MAE bp, trailing 8y

| stratum | code | n exFeb | MAE exFeb | MAE Feb | MAE all |
|---|---|--:|--:|--:|--:|
| Apparel | SAA | 85 | **9.19** ✅ | 17.97 | 9.95 |
| Gasoline | SETB01 | 88 | **18.16** ❌ | 119.53 | 26.61 |
| Used cars | SETA02 | 88 | **16.85** ❌ | 48.93 | 19.52 |
| Airfares | SETG01 | 85 | **14.45** ❌ | 115.44 | 23.14 |

New gate = MAE exFeb < 10bp/MoM. Apparel passes; gasoline/used-cars/airfares FAIL → **HALT**
(pre-defined as "a real finding"). Reroute still HALVES the §2 floor (gasoline 72.9→18.2,
airfares 95.4→14.5 exFeb). February isolates the annual revision: 18–120bp per stratum
(the 3.5bp headline exhibit, generalized).

### Key diagnosis — the ex-Feb residual is the CARRY-FORWARD penalty, not irreducible
Factor itself drifts YoY 25–122bp exFeb (apparel 25 / used cars 59 / gasoline 101 /
airfares 123); MoM impact smaller (9–18bp) via adjacent-month cancellation. BLS PUBLISHES
projected factors and applies them at first release, so first-release factor = BLS published
projected factor → harvesting those files drives exFeb→~0, leaving Feb as the only material
floor. Carry-forward number is an UPPER BOUND.

**Decision options (sa_floor.md §4):** (a) harvest BLS published projected factors
[new pipeline, recommended — expected pass], (b) accept carry-forward + carry the 3 volatile
strata as lead/monitor, (c) model factor drift (same-month AR). Headline/core rows deferred:
no all-items NSA loaded (CUUR0000SA0/SA0L1E absent) — derived by aggregation in Task 5.

Sanity implied factors economically correct: gasoline Jul 1.054 (summer high) / Jan 0.941
(winter low); apparel Jul 0.985 (clearance). 72 tests green. **WAIT for go.**

## TASK 3b RESOLUTION — option (a): harvest BLS published projected factors

User chose (a). Built `pipelines/bls_seasonal_factors/` (edge fetch + license_note + spec)
and naru artifact `pipelines/seasonal_factors_loader/v1/` (golden test passes). Harvested
the annual "Seasonal factors table, YYYY" XLSX for 2021–2026 → **11,604 rows / 194
directly-adjusted series** into `bls_seasonal_factors`, keyed (series_id, reference_period),
stamped `published_asof` = Jan-YYYY CPI release date (from release_calendar).

**Access:** BLS blocks unidentified bots ("Access Denied"); the repo's identifying contact
UA (per _ingest.py) returns files normally. robots.txt permits /cpi/tables/seasonal-adjustment/
*.xlsx (only /*.PDF$ disallowed → pre-2021 PDFs deliberately out of scope). Not a
circumvention; consistent with rule 5. license_note.md records it.

**Identity validation:** harvested published factor == NSA/SA_firstrelease to **0.01 bp** →
it IS the factor BLS applies at first release (test_factors.py).

**Operative floor (factor_conversion_error), MoM MAE bp, trailing 8y:**

| stratum | clean (Mar–Dec) | n | boundary (Jan/Feb) | n |
|---|--:|--:|--:|--:|
| Gasoline SETB01 | **0.02** ✅ | 54 | 130.4 | 10 |
| Used cars SETA02 | **0.02** ✅ | 54 | 44.4 | 10 |
| Airfares SETG01 | **0.02** ✅ | 51 | 130.3 | 10 |

10/12 months/year ~0.02 bp (~750× under carry-forward, 3 orders under the 10 bp gate) →
SA floor **essentially eliminated** for directly-adjusted strata. Residual = the Jan/Feb
annual seam (factors introduced with Jan's own release → real-time forecaster holds prior
year's factor; Feb inherits Jan base). Irreducible calendar fact, carried explicitly.

Apparel/food-at-home/headline are INDIRECTLY adjusted (no direct factor; "–" in file) →
published_factor_asof returns None; SA via component aggregation (Task 5). sa_floor.md §5
rewritten. 6 new tests in test_factors.py. **GATE PASSED for directly-adjusted strata.**

## TASK 4 — NSA-vs-NSA reconciliation reruns

`.env` rechecked: Keepa/USDA/BEA keys still ABSENT → keepa/usda_ams/bea_pce_detail stay
SKIPPED (no builds). reconcile.py: added `official_nsa_mom` (NSA-only, asserts CUUR; leakage-
safe because NSA unrevised), `reconcile_nsa_pair`, `lead_scan_nsa`; refactored shared
`_fit_stability` + `_lead_from` (existing tests green).

**Gasoline (EIA retail vs CPI gasoline), old vs new:**
| pairing | official | n | beta | R² | quality |
|---|---|--:|--:|--:|---|
| OLD | SA CUSR0000SETB01 | 184 | 0.810 | 0.746 | stable |
| NEW | NSA CUUR0000SETB01 | 430 | 0.965 | 0.978 | stable |

R² 0.746→0.978, beta→near-unit pass-through; n doubles (NSA unrevised drops the ~2011 vintage
floor → history back to ~1990); stress R²~0.99 through COVID. The SA-bound was the artifact.

**Manheim used-cars lead scan, old vs new:** lead survives (peak lead-2, stable_leading) but
peak R² FALLS 0.346 (→SA) → 0.197 (→NSA). ASYMMETRY: NSA-vs-NSA helps CONTEMPORANEOUS pairs
(seasonality aligns at lag 0, gasoline) but a leading shift MISALIGNS NSA seasonality →
noisier. Op consequence: use Manheim (lead-2) to predict the deseasonalized used-car part,
then re-apply the harvested factor — do NOT regress NSA-on-NSA for the lead.

3 new tests (test_reconcile.py, 8 total). Report addendum in docs/reconciliation_report.md.

## TASK 5 — CPI aggregation replication + SA-conversion overhead · FINAL CHECKPOINT

Loaded aggregate targets into official_current (were absent): CUUR0000SA0 (1361), CUUR0000SA0L1E
(833), + SA versions — incremental naru official_loader from the existing 2026-07-19 raw pull
(new series_ids, existing rows untouched), 5646 rows.

`src/nowcast/aggregate.py`: price-updated Laspeyres (Dec pivot, annual reweighting) over the
COARSEST complete published partition (each published aggregate embeds BLS's exact
sub-aggregation → coarser is MORE faithful; verified 135-leaf ~2bp worse than 8 majors).
Headline = 8 major groups; core = 15 comps carving out food SAF1 + energy SETB/SEHE/SEHF (~80% wt).

**NSA reconstruction vs official (MoM MAE bp):**
| aggregate | comps | MAE 2023+ | 2021 | full | median |
|---|--:|--:|--:|--:|--:|
| Headline | 8 | **0.50** ✅ | 5.33 | 1.83 | 0.84 |
| Core | 15 | 1.32 | 3.70 | 1.74 | 1.14 |

**Headline MEETS ≤1bp under current (2023+) annual-weight methodology** (2025=0.19bp). Residual
is a methodology-era effect: pre-2023 BLS used BIENNIAL weights → published-RI price-updating
can't reproduce the 2021 surge (5.33bp). Not a machinery error. Rounding floor ~0.2-0.3bp.

**SA-conversion overhead (SA recon − NSA recon, 2023+): headline −0.01bp, core +0.04bp** —
essentially ZERO. Headline/core are INDIRECTLY SA'd (aggregate of component SAs, no headline
factor); aggregate SA error = same top-level weight approx as NSA. Combined with sa_floor §5
(directly-adjusted strata NSA→SA ~0.02bp clean months), the SA pathway is ~free for a good NSA
forecast except the Jan/Feb seam.

nb03_cpi_replication.ipynb (executed), docs/aggregation_error.md, test_aggregate.py (5 tests).
84 tests green. **SESSION 3A COMPLETE.**
