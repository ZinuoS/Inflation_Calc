# Evaluation #1 — prediction layer (Session 4, Task 4)

One harness, purged embargoed walk-forward (embargo 2 mo, min-train 48), first-release targets,
shutdown months skipped. Benchmarks: **AR(1)**, **seasonal-naive** (trailing same-month mean),
**zero**. *Cleveland Fed nowcast is not on FRED and its site export is not yet ingested — a
documented benchmark gap, not a substitute for it.* **Degraded feature set: no Keepa goods panel
— annotated on every H7/H10 result.** Labels not blended with the PURE-OOS machinery tier.

## CPI structured nowcast vs benchmarks — OOS MAE (bp), 2019–2026, n=87

| target | **structured** | seasonal-naive | AR(1) | zero | dir-hit |
|---|--:|--:|--:|--:|--:|
| **headline NSA** | **11.6** | 26.0 | 26.4 | 38.4 | 95% |
| **core NSA** | **12.8** | 16.0 | 16.5 | 32.0 | 95% |

Per-regime (headline): pre-2023 **15.6** vs 32.7 naive; post-2023 **6.7** vs 17.7 naive. The
structured model **beats every benchmark** — ~2× on headline, ~25% on core — with the edge
concentrated in the **energy component** (gasoline is knowable from EIA before CPI prints it) and
the granular per-stratum seasonal baseline. (SA conversion via `factors.py` adds ~0 overhead,
Task-5/3A; direction-hit is high because NSA-MoM sign is largely seasonal.)

## PCE (Instrument A, full-core monitor) — from `oos_report_1.md`

Unbiased (mean signed +0.36 bp) monitor, MAE 7.97 bp, 10–90 band [−11.9, +12.7], boundary
hit-rate 39% ex-COIN-FLIP (**COIN-FLIP** = call within 1.5 bp of a 0.1%-rounding boundary, where
the rounding is a toss-up, reported not scored). Available on **CPI-day, ~2 weeks before the PCE
print** — the value is speed + component attribution, not ≤2.5 bp precision (Instrument B, the
precision sub-aggregate, was terminated).

## H1–H10 verdict table

| H | expectation | test | result | verdict |
|---|---|---|---|---|
| **H1** Manheim mid-month improves used-car surprise (weakly) | lead scan + used-car component | stable_leading, peak R² 0.35 @ lag-2; in the structured model | **SUPPORTED** (weak, as expected) |
| **H2** new-lease rents don't improve next-print shelter (lead ~1yr) | ZORI vs CPI rent/OER, next-print | unstable same-month + calendrically lands after the print | **SUPPORTED** (pre-reg non-win) |
| **H3** bridge beats consensus core PCE post CPI+PPI (matches, rarely beats) | Instrument-A OOS + timing | unbiased ±8 bp, CPI-day (2wk early), BEA attribution; ≤2.5 bp precision FAILED | **SUPPORTED** (matches-not-beats; value=speed+attribution) |
| **H4** freight/commodity leads core-goods 1–2Q (trajectory) | — | freight layer NOT BUILT | **NOT TESTED** |
| **H5** tariff-announcement lags improve core-goods 2025–26 | tariff dummy in VoC feature set | tariff loading small; no dedicated core-goods tariff-lag model beats baseline | **NOT SUPPORTED** (at current scope) |
| **H6** Keepa daily goods panel improves goods nowcast | — | no KEEPA key → NOT BUILT | **NOT TESTED** (degraded) |
| **H7** complexity (ridge/RFF) beats the structured model | purged sweep-curve, decomposed | ridge best 15.3 / RFF 29 > structured 11.5; curves flat; loadings = energy+AR+seasonal | **NOT SUPPORTED — rejected ON AVAILABLE FEATURES** (pre-reg non-win; degraded set, no Keepa daily goods panel — a richer panel is untested, not disproven) |
| **H8** within-month window is identifiable | fold-selection stability | gasoline stable full-month (R² 0.97); heating-oil unstable→default | **SUPPORTED** (for strong proxies; else default) |
| **H9** BEA source mappings (a/b/c) | handbook audit + corr vs 2.4.4U | a: financial≠SEGD05 (still residue); air=PPI ✓; portfolio=PPI corr 0.82 ✓. b: equity-path FALSIFIED. c: drift FALSIFIED OOS→null | **MIXED / mostly falsified** |
| **H10** bridge residual is learnable at CPI-day | ridge/RFF sweep on the wedge | ridge 8.96 (worse) / RFF 8.33 ≈ plain bridge 8.39; no gain | **NOT SUPPORTED — ~7 bp floor irreducible** (pre-reg null) |

None of the pre-registered expected non-wins (H2, H3, H7) surprise-passed, so no leakage audit
was triggered. H10 and H7 both confirmed their nulls with the sweep curves as evidence.

## Admission / demotion — PROPOSALS (Ash decides)

- **ADMIT — structured CPI nowcast** (headline/core): beats all benchmarks ~2× / 25% OOS, skill
  is mechanism-anchored (energy pass-through + seasonal), not overfit. Gasoline pass-through and
  the Manheim lag-2 used-car feature carried within it.
- **KEEP AS MONITOR — PCE Instrument A**: unbiased CPI-day estimate, 2 weeks early, with BEA
  attribution. Not a precision instrument (B terminated); admit as monitor + speed, not as ≤2.5 bp.
- **REJECT — VoC complex models (H7) and the H10 residual model**: no OOS gain; adopting either
  would be complexity for its own sake.
- **DEMOTE to trajectory-only — shelter/ZORI (H2)**: use all-tenant CPI for the next print; ZORI
  as a ~1-yr-ahead trajectory signal only.
- **NOT BUILT (pending) — freight (H4), Keepa goods (H6), a dedicated tariff-lag core-goods model
  (H5)**: no admission possible without the data/build.

## ADMISSION DECISION — signed off 2026-07-22 (Ash)

- **ADMITTED — structured CPI nowcast** (headline + core): the primary instrument.
- **ADMITTED AS MONITOR — PCE Instrument A** (full core): unbiased CPI-day estimate + attribution;
  explicitly NOT a precision instrument.
- **REJECTED ON AVAILABLE FEATURES — VoC complex models (H7) and the H10 residual model**: no OOS
  gain on the **degraded feature set** (no Keepa daily goods panel). The rejection is scoped to the
  features we have — complexity is **untested, not disproven**, on a richer panel; re-test if Keepa
  (or an equivalent daily goods source) ever lands.
- **DEMOTED to trajectory-only — shelter / ZORI (H2)**: all-tenant CPI carries the next print.
- **NOT BUILT (no admission possible)** — freight (H4), Keepa goods (H6), tariff-lag core-goods (H5).

nb05 (intramonth path) is now cleared to go desk-facing.
