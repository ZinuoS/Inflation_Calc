# H11 — sampling-aware seasonal fallback: RESULT

**Pre-registered** in `checkpoint_log_s7.md` §A3, before any fitting. Evaluated in a **shadow
config** (`src/nowcast/h11.py`); `config/component_models.yaml` is untouched.

**VERDICT: NOT ADMITTED.** A pre-registered red flag fired, the mandated audit was run, and the
decomposition shows that most of the apparent gain is **not** the mechanism H11 named.

## What was run

Expanding purged/embargoed walk-forward (embargo 2, min-train 48), first-release NSA targets, AR
coefficients fitted **train-only inside each fold**. Memory length **k swept as a curve**
(1, 2, 3, 4, 6, 12), never tuned to a winner. Baseline = the frozen rule
`s_t + 0.3·(y_{t-1} − s_{t-1})`. H11 = `s_t + AR(k)(deviations)`, applied by **cited** collection
design. `monthly_all_areas` is the **control**: the design predicts no mechanism there.

## Step 1 — the pre-registered RED FLAG fired

Mean per-stratum OOS MAE change (bp), H11 − baseline:

| k | housing_panel (2) | bimonthly (120) | **monthly_all_areas (59) — CONTROL** |
|---|--:|--:|--:|
| 1 | −2.19 | −3.22 | **−4.72** |
| 2 | −2.73 | −3.75 | **−5.02** |
| 3 | −2.65 | −3.47 | **−5.09** |
| 12 | −2.34 | +0.76 | −0.23 |

The gain was **largest in the control class**. A3 pre-registered this exact pattern as a red flag
requiring an audit *before* any admission. The audit follows.

## Step 2 — audit finding A: the threshold was mis-specified, not the mechanism

The A3 red-flag threshold was written in **absolute bp** ("≈ zero, |Δ| < 0.5 bp in
`monthly_all_areas`"). But baseline MAE differs ~15× across the classes:

| design | mean baseline MAE |
|---|--:|
| housing_panel_6 | **8.53 bp** |
| bimonthly | 85.22 bp |
| monthly_all_areas | **130.56 bp** |

0.5 bp on a 130 bp baseline is 0.4% — an unreachable bar. In **relative** terms the concentration
is exactly as pre-registered:

| k | panel | bimonthly | monthly_all |
|---|--:|--:|--:|
| 2 | **−32.4%** | −3.2% | −4.9% |

**The absolute-bp form of the red-flag test was a bad test.** This is recorded as a defect in the
pre-registration, not as a reason to ignore the flag.

## Step 3 — audit finding B: THE CONFOUND (this is what sinks H11)

Decomposing the panel-strata gain into (a) replacing the **frozen 0.3 carry with a fitted
coefficient** (already present at k=1) and (b) the **longer-memory increment** H11 actually named:

| design | (a) fitted-vs-frozen at k=1 | (b) longer memory, best k>1 |
|---|--:|--:|
| housing_panel_6 | **−2.19** | −0.60 (k=2) |
| bimonthly | −3.22 | −0.40 (k=2) |
| monthly_all_areas | −4.72 | −0.51 (k=3) |

**Only 22% of the panel gain (−0.60 of −2.79 bp) is the pre-registered mechanism.** The other 78%
is simply that a fitted carry beats a frozen 0.3 — and the longer-memory increment is **not
design-differentiated** (−0.60 panel vs −0.40 / −0.51 elsewhere). H11 claimed lag *count* matters
for panel strata; the sweep says it barely matters anywhere.

## Step 4 — the headline effect is negligible

| scope | headline MAE (n=88) |
|---|--:|
| baseline | 11.51 bp |
| H11, panel only (pre-registered target) | 11.36 bp (**−0.15**) |
| H11, panel + bimonthly | 11.33 bp (−0.17) |
| H11, all strata incl. control | **12.29 bp (+0.78 — WORSE)** |

A −2.79 bp per-stratum gain on ~33% of weight "should" be ~0.9 bp; it delivers **0.15 bp**.
Component errors partly offset in aggregation, so component-level gains do not propagate. And
applying the rule beyond its design justification makes the headline **worse** — the control class
was right to be a control.

## Verdict and next step

**H11 is NOT ADMITTED.** The frozen config stands.

What is actually true, stated without inflation: the frozen **0.3 carry coefficient is badly
mis-set for high-persistence strata** — panel strata have lag-1 autocorrelation +0.84, so 0.3 is
far too small. That is design-attributable and is the real signal in this experiment. But it is
**not what H11 pre-registered** (lag count), and its headline payoff is ~0.15 bp.

**Next step, to be PRE-REGISTERED BEFORE any further fitting:** a design-conditional *carry
coefficient* hypothesis, with a **matched control** (fitted AR(1) everywhere) so the
fitted-vs-frozen confound cannot masquerade as a design effect again, and with the red-flag
thresholds stated in **relative** terms. It should not be called H11, and it must not reuse this
experiment's numbers as evidence — those are now in-sample with respect to it.
