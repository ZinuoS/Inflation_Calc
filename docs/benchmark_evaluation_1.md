# Benchmark evaluation #1 — "vs the market's number" (Session 8)

Deterministic, offline (`src/nowcast/benchmarks.py`); frozen calls from the Session-6 replay,
nothing refit, no config touched. **Pre-registration:** `checkpoint_log_s8.md`. Market variable =
SA MoM rounded to 0.1pp; our NSA-native call is put on the SA basis with a leakage-safe prior-year
implied factor (validated ~2.5bp headline / ~1.9bp core — a **stated handicap**, not adjusted for).
Rounded (market) and unrounded (our-call) quantities are kept in separate columns.

## Backfill coverage

| benchmark | status | coverage (2023-01 → present) |
|---|---|---|
| **Cleveland Fed nowcast** | INGESTED, vintage-safe | CPI headline **38/42** mo, CPI core **38/42**, PCE core **35** (4 year-boundary months dropped by the as-of safety guard; logged as gaps, not errors) |
| **SPF** (quarterly trajectory) | INGESTED | CPI/core-CPI/PCE/core-PCE, all surveys incl. 2023-01→2026Q2 (336 rows in-window) |
| **Press consensus** | 34 rows / 16-18 mo | Curated via **web search** of cited dated articles (2024-07→2026-06). WebFetch 403; figures taken from search of the named article, contaminated (year-mixed) months dropped as gaps. |

## The three PRE-REGISTERED results (consensus) — VERDICTS

**Consensus panel:** 16 headline / 18 core months, curated via web search of cited dated
articles (2024-07→2026-06; method + no-fabrication discipline in `pipelines/consensus_history/license_note.md`).
The market variable is the rounded consensus median; our NSA call is SA-converted (stated ~2.5/1.9bp handicap).

| claim | headline | core | verdict |
|---|--:|--:|---|
| **PR-3** MAE: ours vs consensus (bp) | 7.54 vs **6.66** | 7.84 vs **6.0** | **NULL HELD** — consensus (later close, superset) beats us modestly, as pre-registered. **No surprise win → no leakage audit triggered.** |
| **PR-1** side-of-consensus, divergence mo | 2/4 = 0.5 (p=1.0) | 5/8 = 0.625 (p=0.7266) | **INCONCLUSIVE (underpowered)** — core 62.5% sits in the pre-registered 55–65% band but n=8 (p=0.73); headline n=4. Not falsified (not ≤50%, not >80%), not confirmed. |
| **PR-2** boundary-month err (bp) | ours 6.01 vs 8.14 (n=5) | ours 6.39 vs 3.44 (n=8) | **MIXED** — headline **better** than consensus; core **worse** (part of the gap is our stated SA-conversion handicap, which bites hardest exactly at rounding boundaries). |

**Reading.** The decisive integrity result is **PR-3**: on an honest, recently-curated consensus
panel we **lose modestly** to a benchmark that closes later and embeds our own signals — precisely
the pre-registered null. Nothing to audit. PR-1/PR-2 are directionally consistent with a weak,
energy-tilted edge but are **underpowered** (4–8 divergence/boundary months); the honest verdict is
*not yet established*, and n grows as the panel is curated back through 2023.

**Reconciliation with the Cleveland analog below.** We "beat" Cleveland on headline (n=81) but lose
to consensus (n=16). No contradiction: the Cleveland win is carried by the **2021–22 energy spikes**
(our admitted gasoline edge, which Cleveland underuses); the consensus panel is **2024-07→2026-06**,
calm in-line months where our gasoline edge is small and the latest-closing consensus edges us. On
the same recent window the two benchmarks agree we have no material average-MAE edge.

## Divergence-month inventory (core, vs consensus) — 14/18 diverge ≥ 0.05pp

| ref | our SA call (pp) | consensus (round) | actual (round) | divergence | ≥0.05 |
|---|--:|--:|--:|--:|:--:|
| 2024-07 | +0.17 | +0.2 | +0.2 | -0.03 | · |
| 2024-08 | +0.14 | +0.2 | +0.3 | -0.06 | ✓ |
| 2024-09 | +0.40 | +0.3 | +0.3 | +0.10 | ✓ |
| 2024-10 | +0.41 | +0.3 | +0.3 | +0.11 | ✓ |
| 2024-11 | +0.29 | +0.3 | +0.3 | -0.01 | · |
| 2024-12 | +0.21 | +0.3 | +0.2 | -0.09 | ✓ |
| 2025-04 | +0.16 | +0.3 | +0.2 | -0.14 | ✓ |
| 2025-05 | +0.16 | +0.3 | +0.1 | -0.14 | ✓ |
| 2025-06 | +0.26 | +0.2 | +0.2 | +0.06 | ✓ |
| 2025-07 | +0.25 | +0.3 | +0.3 | -0.05 | · |
| 2025-08 | +0.24 | +0.3 | +0.3 | -0.06 | ✓ |
| 2025-09 | +0.26 | +0.3 | +0.2 | -0.04 | · |
| 2025-12 | +0.20 | +0.3 | +0.2 | -0.10 | ✓ |
| 2026-01 | +0.40 | +0.3 | +0.3 | +0.10 | ✓ |
| 2026-02 | +0.35 | +0.2 | +0.2 | +0.15 | ✓ |
| 2026-03 | +0.15 | +0.3 | +0.2 | -0.15 | ✓ |
| 2026-04 | +0.21 | +0.3 | +0.4 | -0.09 | ✓ |
| 2026-06 | +0.26 | +0.2 | +0.0 | +0.06 | ✓ |

## Cleveland Fed analog (labelled preview — not the pre-registered consensus test)

n = 81 (2019-2026 replay). Cleveland's nowcast closes ~T-1 — **later than our T-4 freeze** — so it
is a handicapped-superior benchmark, exactly like consensus.

| instrument | our MAE (bp) | Cleveland MAE (bp) | side-rate (divergence mo) | binom p | boundary: ours / Cleveland (bp) |
|---|--:|--:|--:|--:|--:|
| **headline** | **12.39** | 19.18 | 46/54 = **85%** | 0.0 | **11.47** / 21.46 |
| **core** | 13.29 | **10.77** | 24/34 = 71% | 0.0243 | 14.93 / **12.19** |

### This trips a PRE-REGISTERED red flag → AUDIT (belief withheld)

Headline **beats a later-closing benchmark** on MAE and posts an **85% side-rate (> 80% flag)**.
Per the pre-registration, a surprise win → audit *before* belief. Audit findings:

1. **The edge is energy-specific, not a blanket leak.** On **core** we **LOSE** to Cleveland
   (13.3 vs 10.8 bp) — decisive: a firewall breach would help core too. It does not.
2. **The headline edge is gasoline-tilted:** high-gasoline months +7.8 bp vs Cleveland,
   low-gasoline +5.8 bp. Larger where our admitted EIA weekly pass-through bites, consistent with
   mechanism (Cleveland's model underuses weekly retail gasoline) rather than leakage.
3. **Freeze held by construction:** calls are the frozen T-3 replay clamped to T-4; frozen configs
   gate every proxy on `proxy_asof`.

**Verdict on the analog:** the headline "win" is the **already-admitted gasoline edge** showing up
against a benchmark that closes later but underweights weekly fuel data — mechanism-anchored, not a
leak. **Belief is still formally withheld** until the pre-registered *consensus* test runs, per the
pre-registration (do not bless a surprise win on the analog alone).

## Divergence-month inventory (headline, 2023+, vs Cleveland stand-in) — 32/37 diverge ≥ 0.05pp

| ref | our SA call (pp) | Cleveland (round) | actual (round) | divergence | ≥0.05 |
|---|--:|--:|--:|--:|:--:|
| 2023-01 | +0.38 | +0.6 | +0.5 | -0.22 | ✓ |
| 2023-02 | +0.33 | +0.3 | +0.3 | +0.03 | · |
| 2023-03 | +0.11 | +0.5 | +0.1 | -0.39 | ✓ |
| 2023-04 | +0.21 | +0.2 | +0.3 | +0.01 | · |
| 2023-05 | +0.07 | +0.4 | +0.2 | -0.33 | ✓ |
| 2023-06 | +0.20 | +0.3 | +0.2 | -0.10 | ✓ |
| 2023-07 | +0.16 | +0.8 | +0.2 | -0.64 | ✓ |
| 2023-08 | +0.46 | +0.4 | +0.5 | +0.06 | ✓ |
| 2023-09 | +0.46 | +0.2 | +0.4 | +0.26 | ✓ |
| 2023-10 | +0.22 | +0.1 | +0.1 | +0.12 | ✓ |
| 2023-11 | +0.15 | +0.4 | +0.1 | -0.25 | ✓ |
| 2024-01 | +0.14 | +0.4 | +0.3 | -0.26 | ✓ |
| 2024-02 | +0.40 | +0.3 | +0.4 | +0.10 | ✓ |
| 2024-03 | +0.22 | +0.3 | +0.4 | -0.08 | ✓ |
| 2024-04 | +0.27 | +0.1 | +0.2 | +0.17 | ✓ |
| 2024-05 | +0.16 | +0.1 | +0.0 | +0.06 | ✓ |
| 2024-06 | +0.05 | +0.2 | +0.0 | -0.15 | ✓ |
| 2024-07 | +0.16 | +0.2 | +0.2 | -0.04 | · |
| 2024-08 | +0.14 | +0.2 | +0.2 | -0.07 | ✓ |
| 2024-09 | +0.29 | +0.2 | +0.2 | +0.09 | ✓ |
| 2024-10 | +0.37 | +0.3 | +0.3 | +0.07 | ✓ |
| 2024-11 | +0.31 | +0.4 | +0.3 | -0.09 | ✓ |
| 2025-01 | +0.34 | +0.2 | +0.4 | +0.14 | ✓ |
| 2025-02 | +0.30 | +0.0 | +0.2 | +0.30 | ✓ |
| 2025-03 | +0.02 | +0.3 | +0.0 | -0.28 | ✓ |
| 2025-04 | +0.12 | +0.1 | +0.2 | +0.02 | · |
| 2025-05 | +0.11 | +0.2 | +0.1 | -0.09 | ✓ |
| 2025-06 | +0.28 | +0.2 | +0.3 | +0.08 | ✓ |
| 2025-07 | +0.20 | +0.3 | +0.2 | -0.10 | ✓ |
| 2025-08 | +0.30 | +0.4 | +0.3 | -0.10 | ✓ |
| 2025-09 | +0.38 | +0.2 | +0.3 | +0.18 | ✓ |
| 2026-01 | +0.28 | +0.2 | +0.2 | +0.08 | ✓ |
| 2026-02 | +0.34 | +0.5 | +0.3 | -0.17 | ✓ |
| 2026-03 | +0.82 | +0.5 | +0.9 | +0.32 | ✓ |
| 2026-04 | +0.49 | +0.4 | +0.6 | +0.09 | ✓ |
| 2026-05 | +0.48 | +0.1 | +0.5 | +0.38 | ✓ |
| 2026-06 | -0.01 | +0.0 | -0.4 | -0.01 | · |

## SPF — quarterly trajectory (SEPARATE table; not per-print)

Core-CPI median, annualized %, by survey and horizon (h0 = current quarter):

| survey | h0 | h1 | h2 | h3 |
|---|--:|--:|--:|--:|
| 2025Q3 | 2.1 | 3.03 | 3.07 | 2.91 |
| 2025Q4 | 3.3 | 3.2 | 3.1 | 3.0 |
| 2026Q1 | 1.9 | 2.8 | 2.75 | 2.6 |
| 2026Q2 | 2.8 | 3.2 | 2.9 | 2.72 |

SPF is a **trajectory** benchmark: quarterly, annualized, multi-horizon. It is not aligned to a
monthly MoM surprise and is not scored against our per-print call. Our PCE Instrument A call is made
on **CPI-day, ~16 days before the SPF/consensus survey close** — that head start is the instrument's
story, to be scored once a per-print consensus panel exists.
