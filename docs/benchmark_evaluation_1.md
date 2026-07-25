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
| **Press consensus (CPI)** | 30 headline / 27 core mo | Web-search-curated from cited articles, 2023-01→2026-06; year-contaminated months gapped. **PCE-core: 9 mo** (thinner press coverage); **PPI: 0** (not separately previewed in press). |

## The three PRE-REGISTERED results (consensus) — VERDICTS (extended panel)

**Panel (extended Session 8→9):** 30 headline / 27 core months, 2023-01→2026-06, curated via
web search of cited dated articles; year-contaminated months (the 2024/2026 same-month-name trap)
dropped as gaps. **Pre-registration note:** PR-1/PR-2 were underpowered at n=4–8 in Session 8; this
extension is the remedy. **The claims and thresholds are unchanged — no new claims, no threshold
edits.** Market variable = rounded consensus median; our NSA call SA-converted (stated ~2.5/1.9bp handicap).

| claim | headline | core | verdict |
|---|--:|--:|---|
| **PR-3** MAE ours vs consensus (bp) | 7.27 vs 7.33 | 8.53 vs **5.29** | **NULL HELD (core); PARITY (headline).** Core: consensus beats us, as pre-registered. Headline: ours < consensus by **0.06 bp** — a tie that nonetheless tripped the pre-registered audit (below). |
| **PR-1** side-of-consensus, divergence mo | 9/12 = 75% (p=0.146) | 8/12 = 67% (p=0.3877) | **DIRECTIONALLY SUPPORTIVE, NOT SIGNIFICANT.** Both above 50% and in/above the pre-registered 55–65% band; extension lifted n from 4–8 → 12 but neither reaches p<0.05. Not falsified, not confirmed. |
| **PR-2** boundary-month err (bp) | ours 6.47 vs 6.87 (n=9) | ours 8.0 vs 3.16 (n=12) | **MIXED.** Headline no worse than consensus (supported); core worse — largely our stated SA-conversion handicap, which bites hardest at rounding boundaries. |

**PR-3 headline audit (triggered because ours < consensus).** The margin is **0.06 bp — parity, not
a win.** Audit findings: (1) the edge is **balanced** across the gasoline split (high-gasoline months
−0.4 bp, low-gasoline +0.5 bp), i.e. not concentrated where a post-freeze leak would hide; (2) on
**core** (no gasoline) we **lose** 8.53 vs 5.29 bp — a firewall breach would help core too, and it
does not; (3) calls are the frozen T-3 replay clamped to T-4. **Conclusion: no leak.** Headline parity
is the admitted gasoline edge offsetting consensus's later close; belief unchanged (parity ≠ win).

## PCE Instrument A vs press consensus — the speed trade (9 months)

Instrument A calls core-PCE on **CPI-day (~T-16 before the PCE print)** — a full ~16 days before the
survey/consensus close. Consensus therefore closes far later and should win on accuracy; the
instrument's value is the head start + BEA attribution, not precision (pre-registered H3:
matches-not-beats).

| ref | Instrument A (bp) | consensus (bp) | actual (bp) | \|err A\| | \|err cons\| |
|---|--:|--:|--:|--:|--:|
| 2024-04 | +25.4 | +20.0 | +24.9 | 0.4 | 4.9 |
| 2024-09 | +13.4 | +30.0 | +25.4 | 11.9 | 4.6 |
| 2024-11 | +16.4 | +20.0 | +11.5 | 5.0 | 8.5 |
| 2025-07 | +29.4 | +30.0 | +27.3 | 2.1 | 2.7 |
| 2025-09 | +16.6 | +20.0 | +19.8 | 3.2 | 0.2 |
| 2026-02 | +19.4 | +40.0 | +36.7 | 17.2 | 3.3 |
| 2026-03 | +14.1 | +30.0 | +29.3 | 15.2 | 0.7 |
| 2026-04 | +21.5 | +30.0 | +23.9 | 2.4 | 6.1 |
| 2026-05 | +20.1 | +30.0 | +32.0 | 11.9 | 2.0 |
| **MAE** | | | | **7.7** | **3.7** |

Consensus (3.7 bp) beats Instrument A (7.7 bp), as expected for a call made 16 days earlier. The
instrument is close in calm months and misses in the 2026 energy-spike months (2026-02/03, Iran-war
oil) where the bridge struggles — confirming it as a **speed + attribution monitor, not a precision
instrument**, and never scored as one.

## Standing account — where the system sits vs external benchmarks

- **vs the Cleveland Fed nowcast** (closes ~T-1): we hold an **energy-window edge** — headline beats
  it across 2019–2026 (12.4 vs 19.2 bp, n=81), carried by the 2021–22/2023 gasoline spikes where our
  admitted EIA weekly pass-through bites and Cleveland's model underuses it.
- **vs later-closing press consensus** (closes ~T-1 to T-3, after our T-4 freeze): a **modest
  deficit** overall (core 8.5 vs 5.3 bp) shading to **parity on headline** (7.27 vs 7.33) once the
  gasoline edge is in play. No average-MAE win survives against the latest-closing benchmark — the
  honest ceiling of a component nowcast that freezes earlier than the market's own number.
- The two reconcile cleanly: our edge is **energy timing on headline**; on core, and against the
  latest close, we do not beat the market — and we do not claim to.

## Divergence-month inventory (core, vs consensus) — 22/27 diverge ≥ 0.05pp

| ref | our SA call (pp) | consensus (round) | actual (round) | divergence | ≥0.05 |
|---|--:|--:|--:|--:|:--:|
| 2023-02 | +0.35 | +0.4 | +0.5 | -0.05 | ✓ |
| 2023-04 | +0.28 | +0.4 | +0.5 | -0.12 | ✓ |
| 2023-05 | +0.23 | +0.4 | +0.4 | -0.17 | ✓ |
| 2023-06 | +0.18 | +0.3 | +0.2 | -0.12 | ✓ |
| 2023-08 | +0.10 | +0.2 | +0.2 | -0.10 | ✓ |
| 2023-09 | +0.39 | +0.3 | +0.3 | +0.09 | ✓ |
| 2023-10 | +0.42 | +0.3 | +0.3 | +0.12 | ✓ |
| 2023-12 | +0.17 | +0.3 | +0.3 | -0.13 | ✓ |
| 2024-04 | +0.26 | +0.3 | +0.3 | -0.04 | · |
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
