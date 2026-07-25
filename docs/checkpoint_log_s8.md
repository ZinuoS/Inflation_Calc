# Checkpoint log — Session 8 (consensus / survey benchmark construction + evaluation)

## PRE-REGISTRATION (written before ANY evaluation ran)

**Framing.** Consensus is a **handicapped-superior** benchmark: it embeds our own admitted signals
(gasoline, used cars are in every economist's model) and it closes **later than our T-4 freeze**
(preview polls land ~T-1 to T-3; recaps are post-print). So on average it *should* beat us. That is
the null, not the finding. Beating consensus on average MAE is therefore **not** a pre-registered
claim — and a surprise average-MAE win **triggers the standard leakage audit before belief**
(ash-ml-doctrine), because the most likely explanation for beating a later-closing superset is a
firewall leak, not skill.

**The market variable is ROUNDED.** The number the market trades is the print rounded to 0.1pp vs
the consensus median rounded to 0.1pp. Comparisons that use the rounded consensus are kept in a
**separate column** from our unrounded-call metrics; the two are never blended into one statistic
(DO-NOT). The rounding handicap is **stated, not adjusted for**.

**Instruments and freeze.** Our calls: structured CPI nowcast (headline + core) at the **T-3
freeze** (clamped to T-4 internally); PCE Instrument A at its **CPI-day** call — whose story is a
**~16-day head start** on the SPF/consensus close. Benchmarks: **press consensus median**
(point-in-time, article-dated), **Cleveland Fed nowcast** (public, vintage-safe pre-release value),
**SPF** (quarterly, trajectory only — separate table), and the existing AR(1)/seasonal-naive/zero.

### The three PRE-REGISTERED claims under test (with expectations)

**PR-1 — side-of-consensus hit rate, divergence months only.** Restrict to months where our
unrounded call diverges from the rounded consensus by **≥ 0.05pp** (half a rounding unit — where we
are actually saying something different from the market). Claim: in those months, our call lands on
the **correct side of consensus** (same side as the rounded actual) at a rate **> 50%**.
- Expectation: **weakly above 50%** (55–65%), concentrated in energy-driven months where our
  gasoline pass-through gives a real pre-freeze edge.
- Falsification: ≤ 50% (no side information), OR a hit rate so high (> 80%) it implies we are
  reading post-freeze information → **audit**.
- Reported with an exact **two-sided binomial p** against 50%; n stated; COIN-FLIP boundary months
  (call within 1.5bp of a 0.1pp boundary) flagged, reported-not-scored.

**PR-2 — boundary-month performance.** In months where the rounded actual sits within **1.5bp of a
0.1pp rounding boundary** (the print itself is a near-toss-up), report our signed error and the
consensus signed error. Claim: **no worse than consensus** in boundary months (these are where a
component-level unrounded call should, if anywhere, add value over a rounded median).
- Expectation: roughly **parity** (this is a hard set by construction); a modest edge is a bonus.
- Falsification: materially worse than consensus in boundary months.

**PR-3 — average MAE vs consensus (the handicap check, NOT a win claim).** Report our MAE vs
consensus MAE over all covered months, rounded-actual basis for both.
- Expectation (the NULL): **consensus MAE ≤ ours**, by a modest margin, because it closes later and
  is a superset.
- **Trigger:** if ours < consensus (a surprise win), run the leakage audit (re-check the T-4 freeze
  held for every covered month; confirm no proxy read past `proxy_asof`) **before** reporting it as
  a result.

**Method (binding).** Rounded actual = SA MoM (CUSR0000SA0 / CUSR0000SA0L1E) rounded to 0.1pp — the
published market number. PCE core actual = DPCCRG SA MoM rounded to 0.1pp. Our calls come from the
frozen admitted configs via the Session-6 replay (nothing refit). No frozen config is touched.
Consensus rows are point-in-time facts; a month with no verifiable consensus is a **gap row**, never
interpolated, and is simply absent from PR-1/2/3 denominators (n stated honestly).

---

## Data-access findings (recorded honestly, they shape what is buildable)

- **Press consensus auto-backfill is BLOCKED.** WebFetch returns **HTTP 403** on every news outlet
  tried (CNBC, Morningstar, CEPR); the search-snippet summarizer **conflates actual vs expected and
  mixes multiple outlets**, which fails the no-fabrication bar for a cited per-row facts table.
  Per hard rule 5 a blocked source is not fought. `consensus_history` is therefore built as a
  **manual-curation** artifact (schema + license + gap-honest storage + curation protocol); rows
  are added only when a human can open the dated article and read the figure. It ships **gap-first**.
- **Cleveland Fed nowcast: FULLY available and vintage-safe.** The public webchart JSON
  (`nowcast_month.json`) is 157 monthly frames (2013-07→2026-12), each holding the *daily* nowcast
  path; the value immediately before each `CPI/PCE {mon}` vline is the **final pre-release nowcast**.
  Parsed and validated: MAE vs SA actual **0.186pp headline / 0.084pp core** over 152 months —
  matches Cleveland's published accuracy. This gives a real benchmark across the **entire** OOS
  window (42 CPI months, 41 PCE months in 2023+).
- **SPF: available** (Philadelphia Fed median-forecast spreadsheets, public domain).

**Consequence for the checkpoint:** PR-1/2/3 are consensus-specific. With consensus gap-first, they
are reported against **verified consensus coverage only** (n stated); where coverage is
insufficient they are marked AWAITING CURATION rather than fabricated. The Cleveland Fed benchmark
carries the "vs a real external number" evaluation in the meantime.

---

## CHECKPOINT — deliverables

**Pipelines built** (each: fetch.py + spec.yaml + license_note.md):
- `cleveland_nowcast` — INGESTED, vintage-safe, full history (556 rows, 2013-07→2026-12).
- `spf` — INGESTED (2484 rows; 336 in 2023+).
- `consensus_history` — schema + validator + gap-first seed (172 gap rows, 0 curated).

**Storage decision:** benchmarks are derived eval artifacts under `data/benchmarks/*.csv` (like
`event_study_results.csv`), held OUTSIDE `proxy_observations` so a benchmark (itself a forecast of
the target) can never leak into the feature firewall. Network lives only in each `fetch()`.

### Backfill coverage table

| benchmark | curated / total | window | note |
|---|--:|---|---|
| Cleveland Fed CPI headline | 38 / 42 | 2023-01→2026-06 | 4 year-boundary months dropped by as-of guard (gaps) |
| Cleveland Fed CPI core | 38 / 42 | 2023-01→2026-06 | — |
| Cleveland Fed PCE core | 35 / 41 | 2023-01→2026-05 | — |
| SPF (all inflation vars) | full | 2023-01→2026Q2 | quarterly trajectory |
| **Press consensus (CPI)** | 34 rows / 16-18 mo | 2024-07→2026-06 | **web-search-curated from cited articles; contaminated months gapped** |

### Divergence-month inventory
Headline vs Cleveland stand-in, 2023+: **32 of 37 months diverge ≥ 0.05pp** (full table in
`benchmark_evaluation_1.md`). Vs consensus: **awaiting curation**.

### FINAL coverage (curated / total slots), by print type and year — Session 9 extension

| print | variable | 2023 | 2024 | 2025 | 2026 |
|---|---|--|--|--|--|
| CPI | mom_headline | 11/12 | 9/12 | 5/12 | 5/7 |
| CPI | mom_core | 8/12 | 7/12 | 7/12 | 5/7 |
| PCE | mom_core | 0/12 | 3/12 | 2/12 | 4/7 |
| PPI | mom_headline | 0/12 | 0/12 | 0/12 | 0/7 |

**Total: 66 curated / 106 gap of 172 slots.** CPI headline 30, CPI core 27,
PCE-core 9, PPI 0. Gaps are honest: year-contaminated same-month-name months, PCE months lacking a
date-verifiable citation, and PPI (not separately previewed in the press) all stay gaps — never guessed.

### Updated verdicts (extended panel, n=30 headline / 27 core)
- **PR-3:** core NULL HELD (ours 8.53 vs consensus 5.29 bp); headline **PARITY** (7.27 vs 7.33). The
  marginal ours<cons tripped the pre-registered audit → **no leak** (edge balanced across gasoline
  split; we lose on core; frozen freeze). Parity ≠ win.
- **PR-1:** directionally supportive, not significant — headline 9/12=75% (p=0.15), core 8/12=67%
  (p=0.39). Extension lifted n from 4–8 → 12; still short of p<0.05. Claims/thresholds unchanged.
- **PR-2:** mixed — headline no worse than consensus; core worse (SA-conversion handicap at boundaries).
- **PCE Instrument A vs consensus (9 mo):** MAE 7.7 vs 3.7 bp — consensus wins, as expected for a call
  made ~16 days earlier; Instrument A stands as a speed+attribution monitor, not precision.
- **Standing account:** energy-window edge vs Cleveland; modest deficit → headline parity vs
  later-closing consensus. No average-MAE win against the latest close; not claimed.

### Session 9 sign-off notes (recorded before commit)

1. **Audit note (headline parity).** The marginal headline result — ours **7.27** vs consensus
   **7.33 bp**, ours lower by 0.06 bp — satisfied the letter of the pre-registered trigger (ours <
   consensus → audit before belief), so the audit was run. It **cleared with mechanism**: the edge
   is **balanced across the gasoline split** (high-gasoline months −0.4 bp, low-gasoline +0.5 bp),
   not concentrated where a post-freeze leak would hide; and **core was unhelped** (we lose 8.53 vs
   5.29 bp), which a blanket leak would have helped. Freeze held (frozen T-3 replay clamped to T-4).
   **Parity ≠ win — held, not promoted.**

2. **PR-1 status (the one live claim).** Side-of-consensus in divergence months is the single
   **tradeable** claim: headline 9/12 = **75%** (p=0.15), core 8/12 = 67% (p=0.39). It is
   **suggestive but not yet significant** at n=12. The extension exhausted the recoverable press
   history; from here it is **powered up only by forward prints, at ~1 per month**. It stays live
   and unconfirmed — the honest state — accumulating in the pristine ledger.

3. **Instrument A framing.** MAE **7.7 vs 3.7 bp** against consensus is **not a defeat**: the
   consensus number is made ~16 days *later*, right before the PCE print. Instrument A trades ~4 bp
   of precision for a **~16-day head start** — the priced speed/precision tradeoff, exactly the
   pre-registered H3 role (speed + attribution monitor, matches-not-beats). It is scored as a
   monitor, never as a precision instrument.

**Also done (TASK 3c):** `benchmark_evaluation_1.md` written; "vs the market's number" sections
added to `evaluation_1.md` and `oos_report_1.md`; pristine ledger gained `consensus_bp` /
`consensus_asof` columns (populated from the next print forward; the 2026-07 CPI row's consensus
lands ~Aug 10-11 with its own as-of — NOT fabricated now).

**Open decision for sign-off:** press consensus is blocked from auto-backfill. Options — (a) hand-
curate the panel (user opens dated articles), (b) accept Cleveland Fed + SPF as the benchmark set,
(c) provide a licensed/permitted consensus source. PR-1/2/3 run the moment a curated panel exists.

**STATUS: CHECKPOINT — awaiting sign-off.**
