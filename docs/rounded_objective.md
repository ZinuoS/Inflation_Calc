# The ±0.1pp objective — hitting the published tenth

**Why this is the right metric.** BLS and BEA publish to **one decimal place**, and the market reacts
to that rounded number. A call that is 0.03pp off but lands in the wrong tenth reads as *wrong* on the
screen; a call 0.04pp off that lands in the right tenth reads as *right*. So the decision-relevant
metric is the **same-tenth hit rate**, not unrounded MAE. Measured 2026-07-26 from
`data/benchmarks/backtest_vs_consensus.csv`.

## Where we actually stand

| instrument | window | n | **same-tenth hit** | MAE (pp) | MAE ÷ 0.05 |
|---|---|--:|--:|--:|--:|
| cpi_headline | full 2019+ | 88 | **33%** | 0.1186 | 2.4× |
| cpi_headline | 2023+ | 40 | **42%** | 0.0702 | 1.4× |
| cpi_headline | 2025+ tariff | 16 | **44%** | 0.0785 | 1.6× |
| cpi_core | full 2019+ | 88 | 32% | 0.1279 | 2.6× |
| cpi_core | 2023+ | 40 | 35% | 0.0869 | 1.7× |
| pce_core | 2023+ | 40 | 38% | 0.0797 | 1.6× |

**The binding constraint, stated plainly.** To land in the right tenth you generally need
**|error| < 0.05pp** — half an increment. Our error is **1.4× to 2.6× larger than that**. The rounded
objective is therefore *accuracy-bound*, not *rule-bound*: no re-weighting of the objective function
manufactures the missing factor of ~2.

**Sensitivity — what accuracy would be needed** (errors scaled by k, hit rate recomputed):

| instrument | k=1 (now) | k=0.75 | k=0.5 | k=0.25 |
|---|--:|--:|--:|--:|
| cpi_headline | 33% | 43% | **56%** | 69% |
| cpi_core | 32% | 36% | **50%** | 61% |
| pce_core | 38% | 45% | **60%** | 72% |

Even **halving** our error only reaches ~50–60%. And halving is not available: Sessions 7–9 plus the
data-quality and closure sprints established the floor structurally — acquisition closed (4 sources, 0
admissible), H11/H13 rejected, H16 null, H20's aggregate gate failed on the holdout.

## Versus consensus, on consensus months — the sharper standing statement

| instrument | n | ours | consensus | combo(ours,consensus) |
|---|--:|--:|--:|--:|
| cpi_headline | 30 | **43%** | 43% | 43% |
| cpi_core | 27 | 30% | **56%** | 56% |
| pce_core | 9 | 33% | **78%** | 67% |

On the metric that actually drives the headline reaction: we **tie** consensus on headline and **lose
clearly** on core and PCE. This is a blunter version of the MAE finding and it should be quoted that
way — for a *rounded-print* use case the market's own number is better on core/PCE, and our edge
remains **speed + attribution**, not the printed tenth.

## What is legitimately available (pre-registered, NOT done here)

**H22 — boundary-aware rounding rule (decision layer, not accuracy).** When the unrounded call sits
near a tenth boundary, the *reported* tenth could be chosen using our known error distribution
(shade to the side holding more probability mass) instead of naive rounding. This changes the
**decision**, not the forecast; it touches no frozen config and no model.
- **Expectation: small.** It can only rescue months where the call is boundary-adjacent *and* the
  error distribution is asymmetric about that boundary — bounded by a few points of hit rate, not the
  ~2× accuracy gap.
- **Falsification:** no improvement in hit rate on the standard window, or any change in months that
  are not boundary-adjacent (which would mean the rule is doing something other than rounding).
- Must be pre-registered and evaluated in its own session; the gain must be reported in hit-rate
  points with n, and the ~2× accuracy constraint restated so the rule is never mistaken for a fix.

**Not attempted: re-optimising the model toward the rounded objective.** That would change the
objective function of frozen configs, and the measurement above shows why it would not work — the gap
is accuracy, and the accuracy floor has been attacked from four independent directions without moving.
Saying so is more useful than a re-fit that quietly overfits the metric.
