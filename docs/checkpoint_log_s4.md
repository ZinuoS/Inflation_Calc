# Session 4 checkpoint log — the prediction layer

## TASK 0 — push + Keepa
- Held commits f66c30c + ca5b3d4 verified clean (Claude-free author/committer, no data/.env/keys).
  **Push BLOCKED**: this sandbox has no GitHub credential (osxkeychain token gone, no gh, non-
  interactive). Commits remain local at ca5b3d4; origin at dac2f2c. User pushes from their terminal.
- **KEEPA_API_KEY ABSENT** → keepa pipeline NOT built (Task 0c SKIPPED). STANDING ANNOTATION:
  every H7/H8/H10 result carries "degraded feature set (no daily goods panel)". No exceptions.

## H10 — PRE-REGISTRATION (written BEFORE any fitting)

**Hypothesis.** The residual of the Instrument-A bridge (first-release core PCE MoM − bridge
output) contains learnable structure — i.e. the CPI/PPI→PCE commodity-flow "wedge" is partly
predictable at CPI-day from admitted signals + macro state.

**Target.** y_t = official first-release core PCE MoM(t) − Instrument-A bridge call(t), computed
historically ~2015→latest (~110 monthly obs; era-annotated pre/post-2023; shutdown months skipped).
Volatility-standardized (KMZ): y scaled by an expanding-window vol computed INSIDE each fold.

**Feature set (all through the firewalls — proxy_asof / timebase — at measured leads):**
admitted proxies (gasoline NSA, Manheim lag-2, NADAC) + CPI/PPI component relatives (first-release)
+ macro state (broad dollar, front-end rates 2y/3m, energy, tariff-regime dummy dated by
ANNOUNCEMENT not effect) + seasonal harmonics (sin/cos). Features expanding-window-standardized
inside folds (leakage-safe). **DEGRADED: no Keepa daily goods panel — annotated on every result.**

**Models (VoC design, uniform with H7).** intercept ALWAYS in (Buncic). (1) high-dim ridge, z swept
heavy→ridgeless; (2) RFF expansion, P swept ~T/2→~20T. Shrinkage/P tuned ONLY inside purged
embargoed walk-forward folds (embargo ≥2mo). Complexity REPORTED AS A CURVE — "complexity helps"
requires monotone-ish OOS improvement along the sweep, not one lucky (P,z) cell.

**Pre-registered expectation — MODEST.** If the wedge has learnable structure: MAE 7.97→~6-7bp and
boundary hit-rate improves. **NULL RESULT is a real finding**: no OOS gain → "the ~7bp floor is
IRREDUCIBLE at CPI-day", the sweep curve as evidence. Either way the verdict ships in
oos_report_1.md's next revision.

**Adoption gate.** Adopt over the plain bridge ONLY if it (a) beats it on purged walk-forward MAE
AND boundary rate, (b) survives decomposition (loadings must NOT just reconstruct AR/energy/known
structure), (c) degrades gracefully (no fold with catastrophic error). H10 must NOT touch residue
specs (frozen per the standing January-reselection rule).

## TASK 1 — window-alignment layer (windows.py) + H8

### Window taxonomy (proxy spec.yaml `window` blocks)
daily: eia_gasoline(→SETB01), eia_heating_oil(→SEHE01), nadac(→SEMF01), sp500/equity_path(no stratum).
partial: manheim (mid-month=days 1-15 per Manheim methodology; full-month=full; →SETA02).
monthly: tsa (complete-month mean, monitor). event_based (EXEMPT from alignment, leading-only):
zori, atlanta_fed_wage, indeed_wage.

### H8 — PRE-REGISTRATION (written BEFORE fitting)
For each DAILY source × mapped stratum, candidate within-month aggregation schemes:
(1) full_month_mean, (2) bls_three_period_mean (early/mid/late thirds), (3) week_weighted,
(4) trailing_k_day (k∈{7,10,14}). Selection: which scheme's proxy-MoM best tracks the OFFICIAL
NSA stratum relative, chosen INSIDE training folds (expanding walk-forward, embargo ≥2mo) — never
on full sample. Report the winning window per stratum + its STABILITY across folds.
EXPECTATION: a stable, interpretable window (≈ full-month mean for gasoline, whose CPI is a
near-continuous monthly average). An UNSTABLE fold-to-fold winner means the window is NOT
identifiable at our sample size → say so and DEFAULT to full_month_mean rather than fold-chase.
DEGRADED-feature annotation applies (no Keepa goods panel).

### H8 RESULTS + stability verdicts (windows.py select_window, expanding walk-forward, embargo 2mo)
| source → stratum | n_mo | folds | modal window (share) | stable? | SELECTED | test R² | full-month R² |
|---|--:|--:|---|:--:|---|--:|--:|
| eia_gasoline → SETB01 | 430 | 65 | full_month_mean (0.82) | YES | full_month_mean | 0.969 | 0.976 |
| eia_heating_oil → SEHE01 | 478 | 73 | week_weighted (0.51) | NO | full_month_mean (default) | 0.44 | 0.44 |
| nadac → SEMF01 | 58 | 3 | full_month_mean (1.0) | yes | full_month_mean | 0.03 | 0.03 |

VERDICT (matches pre-registration): gasoline's window is STABLE and interpretable ≈ full-month
mean (R²~0.97; full-month is marginally best on test, confirming the default). Heating oil's
winner is NOT IDENTIFIABLE (unstable 51% fold split) → default to full_month_mean per the rule
(no fold-chase). NADAC window is stable full-month but the proxy is WEAK (R²~0.03) regardless of
window — a proxy-quality issue, not a window issue. DEGRADED-feature annotation applies (no
Keepa goods panel). windows.py + partial_feature (Manheim days 1-15 enter as partial). CHECKPOINT 1.

## TASK 2 — structured component models (PRIMARY prediction layer)

src/nowcast/component_models.py + config/component_models.yaml (FROZEN). Per-stratum first-release
NSA MoM forecast, boring by design:
- SETB01 gasoline: IMPOSED pass-through (beta 0.965, retail->CPI, NOT fit) of EIA gasoline
  full-month mean (H8 window).
- SETA02 used cars: lead_feature, Manheim lag-2 (beta 0.497 from lead_profile, re-fit in folds).
- default: seasonal_ar baseline = mean of trailing 8y same-calendar-month NSA MoMs + 0.3 AR(1)
  carry of last print's deviation (captures the dominant NSA seasonal shape).
Firewall: proxy reads gated to obs publishable at forecast_time (proxy_timebase) + H8 window
(windows.py); stratum history uses only printed months (NSA unrevised). Forecast at LEAF-stratum
level (180 comps headline / 116 core) so stratum proxies apply, Laspeyres-aggregated (aggregate.py
weights). SA via factors.py + PCE via bridge = reuse validated modules, exercised in Task-4 eval.

SMOKE (2024-25, NSA MoM vs actual first-release, betas frozen — NOT the purged eval, that's T4):
headline MAE 5.3bp (was 10.0 seasonal-only 8-major; proxies+finer baseline), core 6.2bp;
2 proxy-driven comps (proxy_wt 5.8% headline). DEGRADED feature set (no Keepa goods panel).

## TASK 3 — H7 VoC (value-of-complexity) CHALLENGER — PRE-REGISTRATION (before fitting)

**Claim under test.** A high-dimensional model over the full admitted feature set beats the
parsimonious structured model (Task 2) at nowcasting headline/core NSA MoM.
**Design (VoC notes, uniform with H10).** intercept ALWAYS in (Buncic); target volatility-
standardized, features expanding-window-standardized INSIDE folds (leakage-safe). Two families:
(1) high-dim RIDGE, shrinkage z swept heavy→ridgeless; (2) RANDOM FOURIER FEATURES, P swept
~T/2→~20T. Feature set: admitted proxies (gasoline full-month, Manheim lag-2, NADAC) + macro
state (broad dollar, 2y rate, WTI energy, tariff-regime dummy dated by ANNOUNCEMENT) + seasonal
harmonics + lags(1-3) + a few interactions — all knowable at CPI-day, through the firewalls.
Evaluation: SAME purged embargoed walk-forward folds/target as Task 2.
**COMPLEXITY REPORTED AS A CURVE:** "complexity helps" requires monotone-ish OOS improvement along
the z / P sweep, NOT one lucky (P,z) cell.
**PRE-REGISTERED EXPECTATION (Nagel/Buncic):** MATCHES but does NOT BEAT the structured model on
OOS MAE / hit-rate. Any apparent win must ALSO beat AR(1) + Cleveland Fed (Task-4 benchmarks) AND
be DECOMPOSED — if loadings reconstruct AR + energy pass-through, it rediscovered known structure
→ verdict NOT SUPPORTED. Complexity wins on accuracy or not at all; no Sharpe channel in a nowcast.
DEGRADED feature set (no Keepa goods panel) — annotated on every H7 result.

### H7 VoC RESULTS + VERDICT (purged walk-forward, 2015-2026, 88 scored months)
BASELINES OOS MAE bp: **structured (Task 2) = 11.51**; naive AR(1)=lag1 26.15; zero 37.96.
RIDGE sweep (z heavy→ridgeless): 33.9(z1000)→15.4(z10)→**15.26(z3,best)**→15.4(ridgeless) — FLAT
from z=3 on, no complexity benefit. RFF sweep (P ~0.4T→19T): 28-32bp, FLAT/noisy, NO monotone
P-improvement. **Complexity fails its own "monotone-ish OOS improvement" criterion on both curves.**
Best challenger (ridge 15.3bp) is WORSE than structured (11.5bp); RFF (29bp) far worse.
DECOMPOSITION (ridge z=3 loadings): top = gasoline +0.54 (energy), lag1/lag3 (AR), sin1/sin2
(seasonal); energy 37% + seasonal 22% of |loadings| = the challenger's signal IS the known
structure the parsimonious model imposes directly & better.
**H7 VERDICT: NOT SUPPORTED** — complexity does not beat parsimony (matches the pre-registered
Nagel/Buncic expectation; here it doesn't even match). No Sharpe channel; complexity must win on
accuracy and it does not. DEGRADED feature set (no Keepa goods panel). voc.py + test_voc.py.
Full benchmark table (AR(1)+Cleveland Fed+zero, SA/PCE targets, H1-H10) is Task 4.

## TASK 4 — EVALUATION HARNESS + H10 + H1-H10 VERDICTS · CHECKPOINT 2

H10 (bridge-residual learnability, fit now): target = first-release core PCE MoM − Instrument-A
bridge output (123mo, std 9.8bp). plain-bridge baseline OOS MAE 8.39bp; ridge best 8.96 (WORSE,
only "helps" by shrinking→bridge); RFF plateaus 8.33 (≈baseline). **H10 NULL — ~7bp floor
IRREDUCIBLE at CPI-day** (pre-registered null confirmed; sweep curve = evidence).

CPI structured nowcast vs benchmarks (purged walk-forward 2019-2026, n=87, NSA MoM):
headline structured 11.6bp vs seasonal-naive 26.0 / AR(1) 26.4 / zero 38.4 (post-23: 6.7 vs 17.7);
core 12.8 vs 16.0 / 16.5 / 32.0. **STRUCTURED BEATS ALL BENCHMARKS ~2x/25%** (edge from energy
predictability + granular seasonal). Cleveland Fed benchmark = documented gap (not on FRED).

H1-H10 verdicts (docs/evaluation_1.md): H1 SUPPORTED(weak); H2 SUPPORTED(pre-reg non-win);
H3 SUPPORTED(matches-not-beats, value=speed+attribution); H4 NOT TESTED(freight not built);
H5 NOT SUPPORTED(scope); H6 NOT TESTED(no Keepa); H7 NOT SUPPORTED(pre-reg non-win); H8
SUPPORTED(strong proxies); H9 MIXED/mostly falsified; H10 NOT SUPPORTED(floor irreducible).
No pre-reg non-win surprise-passed → no leakage audit needed.

ADMISSION PROPOSALS (Ash decides): ADMIT structured CPI nowcast (beats benchmarks, mechanism-
anchored); KEEP PCE Instrument A as monitor (unbiased, CPI-day, attribution — not precision);
REJECT VoC/H10 complex models (no OOS gain); DEMOTE shelter/ZORI to trajectory-only; NOT BUILT
freight/Keepa/tariff-lag. docs/evaluation_1.md. voc.py H10 reuse. WAIT for admission/demotion.

## TASK 5 — intramonth T-minus monitor (operational)

src/nowcast/intramonth.py: nowcast_as_of(ref_month, as_of, aggregate) = best estimate using only
info observable at as_of (proxies gated by proxy_timebase + H8 window; stratum history = printed
months only). FREEZE ENFORCED (not just documented): as_of past T-4 clamped to T-4 (availability
calendar — last useful input ~4d before print). tminus_path (T-30→T-3) + backtest_curve (MAE vs
days-to-release). Perf: shared DB connection through the aggregate (was 180 conns/call).

**T-minus MAE curve (CPI headline, last 18 prints 2024-11..2026-06, bp):**
T-30 10.3 → T-24 8.8 → T-18 8.9 → T-12 8.1 → T-8 7.5 → T-5 7.5 → T-3 7.5 (frozen T-4).
The honest "how early do we know what we know": the estimate converges by ~T-8 as month-M gasoline
(EIA) completes + Manheim lands, and improves NOTHING after T-4 (freeze). ~7.5bp recent-regime
floor (vs 11.6bp on the fuller 2019-26 window incl. the 2021-22 surge). nb05 = one print's path.
DEGRADED feature set (no Keepa). test_intramonth. Desk-facing only after admission sign-off.
