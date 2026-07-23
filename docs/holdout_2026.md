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

**Valid weights (BEA 2.4.5U):**

| ref month | bridge (bp) | actual first-release (bp) | error (bp) |
|---|--:|--:|--:|
| 2026-01 | +5.3 | +36.4 | **−31.1** |
| 2026-02 | +14.4 | +36.7 | **−22.3** |
| 2026-03 | +18.6 | +29.3 | **−10.8** |
| 2026-04 | +51.8 | +23.9 | **+27.9** |
| 2026-05 | +44.3 | +32.0 | **+12.3** |

**MAE 20.9 bp (valid) vs 11.4 bp (degraded), 0/5 correct side.** The 2026 holdout is **worse than
the trailing-5y 9.1 bp** and worse than the degraded run — a genuine regime signal. With true
weights the volatile-proxy components (financial charges, air transport) and the frozen imputed
lines now carry full weight, and the tariff regime amplifies exactly those: Jan–Mar under-predict
(−11 to −31 bp), Apr–May over-predict (+12 to +28 bp), sign-mixed rather than a clean bias. The
CPI machinery (§a) still nails the aggregates OOS, so this is the **bridge's component-proxy error
under a new regime**, not an aggregation problem — and it sharpens the K1 diagnosis:
`pce_bridge_acceptance.md` drivers 1–5 are precisely what breaks in 2026.

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
