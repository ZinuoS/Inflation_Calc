# 2026 out-of-sample holdout (Session 3B, Task 2b)

Every 2026 print released as of 2026-07-20, enumerated from `release_calendar`: **CPI/PPI
reference months Jan–Jun 2026, PCE Jan–May 2026**. These months are **strictly outside every
estimation window** (all frozen terms are ≤2022; the 2026 CPI RI table is not even published
yet — we fall back to 2025 weights, a documented staleness caveat) **and inside the tariff
regime**. This is the single most honest accuracy evidence the project has.

**Scope — replication vs forecast (do not conflate).** §a and §c measure **replication**
accuracy: *given the released CPI/PPI component prints*, how well do we assemble the aggregates
and the PCE bridge. Pre-print **forecast** accuracy for CPI/PPI does not exist until Session-4's
component models. The tables below are replication only.

## §a — CPI machinery check (reconstruct 2026 prints from first-release components)

Reconstruction vs official first-release, MoM error (bp), per month, via `aggregate.py`
(coarsest complete published partition; **2025 weights** — 2026 RI table not yet published):

| aggregate | space | MAE | Jan | Feb | Mar | Apr | May | Jun |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| Headline | NSA | **0.02** | 0.01 | 0.01 | 0.01 | 0.03 | 0.02 | 0.01 |
| Headline | SA | **0.39** | 0.22 | 0.04 | 1.02 | 0.22 | 0.23 | 0.63 |
| Core | NSA | **0.02** | 0.01 | 0.01 | 0.01 | 0.02 | 0.02 | 0.03 |
| Core | SA | **0.71** | 2.82 | 0.58 | 0.27 | 0.30 | 0.01 | 0.27 |

**The aggregation machinery holds out of sample in the tariff regime** — NSA reconstruction is
at the rounding floor (~0.02 bp) even with stale weights; SA is ≤~0.7 bp (the Jan core-SA 2.82
bp is the annual factor-seam month). This confirms Session 3A's result generalizes to 2026 and
isolates the bridge failure (§b) to the PCE weights, not the assembly.

## §b — PCE bridge holdout (post-CPI+PPI call vs first-release core PCE)

| ref month | bridge (bp) | actual first-release (bp) | error (bp) | correct side? |
|---|--:|--:|--:|:--:|
| 2026-01 | +23.0 | +36.4 | **−13.4** | ✗ |
| 2026-02 | +21.0 | +36.7 | **−15.7** | ✗ (Feb factor seam) |
| 2026-03 | +19.6 | +29.3 | **−9.7** | ✗ |
| 2026-04 | +35.1 | +23.9 | **+11.2** | ✗ (coin-flip) |
| 2026-05 | +24.9 | +32.0 | **−7.1** | ✗ (coin-flip) |

**MAE 11.4 bp, 0/5 correct side.** The bridge **under-predicts** 2026 core PCE (actual runs hot
at ~30–37 bp; bridge ~20–35), the **opposite sign** to its 2020–22 over-prediction — direct
evidence the error is regime-dependent weight error, not a constant bias (see
`pce_bridge_acceptance.md`). Consistent with the tariff regime lifting goods/healthcare
categories that the CPI-RI proxy under-weights or cannot see.

## §c — PPI machinery check — NOT RUN (weights unavailable)

PPI final-demand reconstruction requires PPI final-demand component weights, which are **not
ingested** (no PPI weight table; the same class of gap as the PCE weights). Reconstructing PPI
FD from components is therefore out of scope until those weights land. The PPI *component*
prints themselves are used by the bridge (healthcare, air transport) and are covered above.

## Bottom line

Machinery (CPI aggregation) — **passes out of sample, ≤0.7 bp**. Bridge (PCE) — **fails, 11.4
bp**, same root cause as the 5-year gate: missing BEA PCE weights. The 2026 evidence *sharpens*
the diagnosis (regime sign-flip) rather than softening it. Travels with
`pce_bridge_acceptance.md` as the gate's out-of-sample companion.
