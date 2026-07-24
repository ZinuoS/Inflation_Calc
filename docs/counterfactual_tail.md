# Counterfactual tail — what the un-acquirable strata actually cost

**This is a RECORD, not a performance claim.** Nothing here is admitted, and no configuration is
changed by it. It answers one question: *if Part B had succeeded perfectly — if lodging, wireless,
electricity and insurance had each been forecast with no error at all — how much better would the
CPI headline nowcast have been?*

**Method.** The Session-6 event-study replay (`docs/event_study_results.csv`, frozen admitted
configs, T-3 freeze, **nothing refit**) supplies the actual call and deviation for each of 88
evaluable prints, 2019-01 → 2026-06. For each print, each target stratum's own model forecast is
replaced by its realized NSA MoM, and the difference is removed from the aggregate at that year's
Laspeyres relative importance. `cf_hard` substitutes only the **hard-conceded** strata (S1 lodging,
S2 wireless, S4 electricity); `cf_all4` also substitutes **S3 insurance**, which is held open
pending H11b.

## Aggregate effect of perfect foresight (n=88)

| statistic | actual | cf_hard | cf_all4 |
|---|--:|--:|--:|
| **MAE (bp)** | **11.51** | 10.25 | **9.60** |
| p90 \|deviation\| | 29.8 | 29.5 | 24.9 |
| **max \|deviation\|** | **62.4** | **64.3** | **63.2** |

**Two findings, both awkward for the acquisition premise:**

1. **Perfect foresight on all four strata buys 1.9 bp of MAE** (11.51 → 9.60, a 17% reduction).
   That is the *ceiling* on what Part B could ever have delivered — achieved only with zero
   forecast error, which no real feed provides. The realistic yield was a fraction of it.
2. **It does not improve the worst month at all — it makes it slightly worse** (62.4 → 63.2 bp).
   In the largest miss (2022-06) these strata's errors were *offsetting* part of the total error.
   Across all 88 months they point the same way as the total error only **66/88 (75%)**
   of the time. **Acquisition was never a tail-risk fix.**

## The tail (June-2026 first, then the 9 largest misses)

Per-stratum columns are each stratum's weighted contribution to the deviation, in bp. Positive =
the model over-predicted that stratum, inflating the miss.

| ref month | deviation | cf_hard | cf_all4 | lodging | wireless | electricity | insurance |
|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-06 | +42.4 | +29.3 | +20.9 | +4.0 | +5.1 | +3.9 | +8.4 |
| 2022-06 | -62.4 | -64.3 | -63.2 | +2.6 | +0.1 | -0.9 | -1.0 |
| 2022-05 | -57.3 | -58.2 | -56.2 | +1.2 | -0.2 | -0.1 | -2.1 |
| 2021-04 | -53.6 | -43.9 | -41.3 | -6.3 | -0.0 | -3.4 | -2.6 |
| 2021-10 | -52.3 | -45.2 | -47.5 | -0.1 | -0.1 | -6.9 | +2.3 |
| 2022-03 | -41.7 | -32.7 | -32.1 | -3.0 | -0.2 | -5.9 | -0.5 |
| 2022-04 | -36.7 | -33.5 | -30.5 | -1.4 | -0.2 | -1.6 | -3.0 |
| 2021-06 | -36.0 | -32.8 | -35.4 | -6.0 | -0.2 | +2.9 | +2.6 |
| 2022-01 | -33.1 | -30.0 | -27.9 | +5.9 | -0.0 | -9.0 | -2.1 |
| 2020-04 | +28.4 | +25.3 | +12.0 | +3.9 | -0.2 | -0.6 | +13.3 |

## Why June-2026 misled us

**June-2026 is the exception, not the pattern.** It is the one month where all four strata erred in
the *same* direction simultaneously (+4.0, +5.1, +3.9, +8.4 = +21.4 bp of a +42.4 bp miss), which
is why the postmortem read as a data-acquisition problem. The rest of the tail is dominated by the
2021–22 surge, where misses were **broad-based** and these four contributed little or offset:
2022-06 (−62.4 bp) has a combined contribution of **+0.6 bp**, and 2022-05 (−57.3) just **−1.2**.

Mean |combined contribution| across all months is **4.22 bp**, max **22.2 bp**.

**Consequence for the research plan.** The session opened on the premise that the June miss was a
sourcing gap and that acquisition would close it. The counterfactual says the ceiling on that
programme was ~1.9 bp of MAE with no tail benefit — and Part B then showed even that ceiling was
unreachable, for four independent reasons. The remaining headroom is in **baseline specification**
(H11 / H11b), which is exactly where the Part-A audit pointed and where the evidence (panel
autocorrelation +0.84/+0.80; bimonthly lag-2 t = −5.58) is strongest.
