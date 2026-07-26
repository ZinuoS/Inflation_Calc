# Checkpoint log — H20 (forward-published factors) · H19 (forecast combination) · forward vintage capture

Ledger rows untouched; no adjudication before 2026-07-30; frozen configs touched **only** via H20's
adoption gate. Residue specs not touched. H19 is a **reporting-layer** product and is never presented
as an accuracy claim about "ours".

**BOTH HYPOTHESES PRE-REGISTERED IN FULL BEFORE ANY BUILD (this section written first).**
Frozen-config guard verified green first.

---

## H20 — forward-published CPI seasonal factors

### Research question: ANSWERED **YES**, with citations (checked 2026-07-25)

**Primary source** — `bls.gov/cpi/seasonal-adjustment/home.htm`, verbatim:

> "Updated seasonal factors introduced February 13, 2026"
> "Each year with the release of the January CPI, seasonal adjustment factors are recalculated to
> reflect price movements from the just-completed calendar year. This routine annual recalculation may
> result in revisions to seasonally adjusted indexes for the previous 5 years."

**We already ingest them.** `pipelines/bls_seasonal_factors` → table `bls_seasonal_factors`: **11,604
rows, 194 series, factor years 2021–2026**, each with `published_asof` ∈ {2021-02-08, 2022-02-08,
2023-02-10, 2024-02-09, 2025-02-12, **2026-02-13**} — the Feb dates match the BLS page exactly. The
Feb-2026 publication carries projected factors for **all twelve months of 2026** (reference_period
2026-01 → 2026-12), i.e. genuinely **forward**. Session 3A already verified the harvested factor **is**
the applied factor (equal to NSA/SA first release to 0.01 bp).

**So H20 is not a discovery task — it is a plumbing gap.** `benchmarks.our_call_sa_pct` (the SA
conversion used for every consensus comparison, PR-1/PR-2/PR-3 and the backtest CSV) does **not** use
these published factors. It uses a **prior-year same-month implied factor** (NSA/SA of month *m*−12),
measured at **~0.025 pp headline / ~0.019 pp core** of added error. That is the quantity H20 attacks.

**Two facts that constrain the build:**
1. **Aggregates are INDIRECTLY adjusted.** `SA0`, `SA0L1E`, `SAA`, `SAF11` have **0** published direct
   factors — BLS derives them by aggregating adjusted components. Only **88 of 181** leaf strata carry
   published 2026 factors. So the aggregate factor must be **constructed** from published component
   factors (BLS's own indirect method), not looked up.
2. **The January seam is a hard leakage boundary.** Year-*Y* factors publish *with the January-Y CPI
   print* (e.g. 2026-02-13 **is** the Jan-2026 release date). Our freeze is **T-3**, i.e. *before* that
   print. Therefore: for reference months **February–December of year Y**, year-*Y* published factors
   are available at the freeze; for reference month **January of year Y** they are **not** — January
   must fall back to year-(*Y*−1) factors. Any run that uses year-*Y* factors for January-*Y* is
   look-ahead and is **disqualified**, not reported as a win.

### Build
Add a `published_forward` resolution path to the SA conversion: for reference month *m*, use the
published projected factor whose `published_asof` ≤ freeze date, preferring the **current-year** factor
where legal (Feb–Dec) and falling back to **prior-year carry** otherwise (January, and any stratum
without a published factor). Aggregate component factors to the headline/core level via the existing
`aggregate.py` partition machinery. Retain both arms: **CARRY** (current frozen behaviour) and
**PUBLISHED-FORWARD**.

### Pre-registered expectation
SA-conversion error falls materially for **Feb–Dec** months (the published factor *is* the applied
factor, so the residual should approach the **aggregation** floor ~0.005 pp rather than the
**extrapolation** floor ~0.025 pp). **January unchanged by construction** — assert this as a test; a
January change means a leakage bug. Net effect on the consensus head-to-head should be visible where
we currently lose: **core** (ours 0.0853 vs consensus 0.0529 pp) and **PR-2 boundary months**.

### Adoption gate (all three; Ash decides)
1. SA-conversion error **drops** on the standard window, **AND**
2. non-seam months **unchanged or improved** (no month degrades materially), **AND**
3. the improvement **replicates on the 2026 holdout**.

Report the **PR-2 and core head-to-head deltas** explicitly — that is the target.

### Red flags → audit before adoption
- Any change in a **January** month ⇒ leakage (year-*Y* factors used before publication).
- Improvement larger than the currently-measured conversion handicap (~0.025 pp) ⇒ the arms differ in
  something other than the factor source.
- **IF the research question had been NO:** the prior-year carry would be *proven optimal-available*,
  upgrading the seam constant from "handicap" to "floor". It is **YES**, so that branch does not apply
  — but note H13 already proved the *February revision* is unpredictable, so the January seam remains
  a floor regardless of H20's outcome.

---

## H19 — forecast combination (REPORTING LAYER ONLY)

### Build
Convex combination `combo = w·ours + (1−w)·consensus`, evaluated on consensus months for all three
instruments (`cpi_headline`, `cpi_core`, `pce_core`), in **pp**.

**Weight selection, decided by fold stability and documented either way:**
- Estimate *w* on the **Cleveland panel, pre-2023 portion only** (frozen once estimated; pre-2023 is
  outside the consensus evaluation window, so the estimate is not fitted to the months it is scored on).
- **IF the estimate is unstable across folds** (sign flips, or spread > ~0.25), fall back to the
  **pre-committed w = 0.25**. Which path was taken is recorded explicitly.

### Pre-registered expectation
- **Headline combo beats consensus alone** — our energy timing (EIA weekly gasoline) is genuinely
  orthogonal to a survey median, and headline is where we already reach parity.
- **Core ties or loses slightly** — we have no core edge, so blending mostly re-weights consensus.
- **Any dramatic win triggers the audit** (a large gain would more likely indicate the consensus panel
  or the SA basis is misaligned than that a 2-term convex blend found free skill).

### Standing labelling rule (binding, not optional)
A combo number is **never** an accuracy claim about "ours". It is a **combination product** and must be
labelled `combo(ours,consensus)` wherever it appears. It does **not** touch the primary instruments,
the frozen configs, or the existing ledger rows. If adopted, combo calls may join the ledger **as a
distinct instrument label** from the next freeze forward — never retrofitted to past rows.

---

## TASK 3 — forward vintage capture (infrastructure, no hypothesis)

Every pull of a `revised_latest_only` source (**ATRR**, **ZORI**, **Apartment List**, and any future
one) archives the **full history snapshot** under `data/raw/{source}/vintage_{date}/` with a manifest
(source, url, retrieved_at, sha256, row count, period range). A test asserts snapshots are
**immutable** (an existing vintage directory is never overwritten or mutated).

**Why:** H14 (ATRR rent carry) failed *only* on vintage integrity — the lead is real and stable
(SEHA +0.86 / OER +0.84, stable across four sub-periods) but the gain was measured on **revised** data
and BLS publishes no ATRR vintage archive. Once we hold ~4 quarters of our **own** snapshots, H14
becomes **pristinely re-runnable on our own archive**. Calendar entry: **2027-07 re-evaluation**.

---

**STATUS: PRE-REGISTRATION COMPLETE. Proceeding to H20 → CHECKPOINT H20, wait.**

---

## CHECKPOINT H20 — **RESEARCH QUESTION: YES. AGGREGATE ADOPTION: NO (gate fails on the holdout).**
## But the component-level finding is large and is the real result.

### 1. Research question — answered YES, cited

`bls.gov/cpi/seasonal-adjustment/home.htm`, verbatim: *"Updated seasonal factors introduced
**February 13, 2026**"* / *"**Each year with the release of the January CPI**, seasonal adjustment
factors are recalculated…"*. Our harvested table's `published_asof` values
(2021-02-08 … **2026-02-13**) match the page exactly, and the Feb-2026 publication carries projected
factors for **all twelve months of 2026** — genuinely forward. **BLS does publish forward factors, and
we already ingest them** (11,604 rows, 194 series, 2021–2026).

So the prior-year carry is **NOT** proven optimal-available. The "IF NO" branch of the
pre-registration does not apply.

### 2. A TARGET ERROR IN MY FIRST TWO RUNS — found and corrected mid-checkpoint

My first two runs scored both arms against **latest-vintage** SA (`CUSR0000SA0`) and concluded
published factors were ~2–4× *worse*. That was wrong, and the reason matters: BLS **revises SA indexes
for the previous 5 years** at each annual recalculation (cited above). The published projected factor
reproduces the **first release**, not today's revised series. Scoring it against revised data measures
the revision, not the factor.

Re-run against **first-release SA** (`first_release_mom`, the number consensus forecasts and the market
trades) — the result inverts completely:

| stratum | carry (pp) | **published-forward (pp)** | delta |
|---|--:|--:|--:|
| SETB01 gasoline | 0.9922 | **0.0002** | **−0.9920** |
| SETA02 used cars | 0.5652 | **0.0002** | **−0.5650** |
| SEHF01 electricity | 0.1839 | **0.0002** | **−0.1837** |
| SEHC01 OER | 0.0153 | **0.0001** | −0.0152 |
| SEHA rent | 0.0132 | **0.0001** | −0.0131 |

**At component level the published factor is essentially EXACT (0.0002 pp = 0.02 bp)**, confirming
Session 3A's finding that the harvested factor *is* the applied factor. Carry costs up to **0.99 pp**
on gasoline. This is a large, real, previously-unexploited improvement — **but it lives at the
component level.**

### 3. Aggregate adoption — GATE FAILS

`SA0`/`SA0L1E` are **indirectly adjusted** (0 published direct factors), so the aggregate factor must
be *constructed* from component factors (BLS's own indirect logic:
`F_agg = Σw·NSA / Σw·(NSA/F)`), with per-stratum carry fallback where no published factor exists
(**coverage 64% of weight**). Against first-release SA:

| instrument | legacy (agg-implied carry) | carry-built | **published-built** |
|---|--:|--:|--:|
| cpi_headline | 0.0509 | 0.0542 | **0.0483** |
| cpi_core | **0.0420** | 0.0527 | 0.0523 |

| gate condition | headline | core |
|---|---|---|
| 1. error drops on standard window | ✅ (0.0483 < 0.0509) | ❌ (0.0523 > 0.0420) |
| 2. non-seam unchanged/improved | ✅ Feb–Dec −0.0103 | ❌ Feb–Dec +0.0057 |
| **3. replicates on 2026 holdout** | ❌ **+0.0206** | ❌ **+0.0394** |

**Gate fails on condition 3 for both instruments → NOT ADOPTED. Frozen configs untouched;
`benchmarks.our_call_sa_pct` unchanged.**

**Why the component gain does not survive aggregation:** only 64% of weight has a published factor, so
the constructed aggregate mixes two factor sources; and the reconstruction pays the ~0.5 bp
partition-replication penalty that the legacy *aggregate-implied* factor avoids by construction (it is
BLS's own aggregate ratio, internally consistent with their exact structure). **The bottleneck is the
indirect-aggregation reconstruction, not the factor source.**

### 4. Pre-registration defect, recorded

I asserted *"January unchanged by construction — a January change means a leakage bug."* January **did**
change (headline +0.0867 pp), and that assertion was **imprecise, not violated**: both arms fall back
in January, but to *different* quantities (prior-year **published** vs prior-year **implied**).
**Leakage audit run explicitly** — for all five Januaries (2022–2026) the count of current-year factor
rows usable at the T-3 freeze is **0**; factors publish on the January release date, our freeze is 3
days earlier, and the `published_asof < ft` guard correctly excludes them. **No leakage.**

### 5. Second discovery — a TARGET-DEFINITION issue in the benchmark comparison (not in scope; flagged)

`benchmarks.actual_sa_mom_pct` uses **latest-vintage** SA as "actual", but **consensus forecasts the
first release**. The two differ materially: **|first-release − latest-vintage| SA MoM = 0.0480 pp mean,
0.2201 pp max (headline)** — against a consensus head-to-head MAE of ~0.073 pp. Our legacy conversion
also scores better against latest-vintage (0.0291) than first-release (0.0509), i.e. it is aligned to
the *wrong* target for this comparison.

**Not changed this session.** Altering the actual-target would silently move PR-1/PR-2/PR-3, which have
recorded pre-registered verdicts — that is re-litigating a result, not fixing a bug. Recorded as a
**pre-registration candidate (H21)**: re-score the consensus head-to-head on first-release SA for both
sides, pre-registering that our numbers may get *worse*.

### Admission proposal
**REJECT for the aggregate SA conversion** (gate condition 3). **Flag as high-value for a future
pre-registered H21**: apply published factors at the **component** level *inside* the forecast path
(convert each stratum NSA→SA with its published factor, then aggregate SA), which is where the
0.0002 pp exactness lives — plus the first-release target fix. Neither is done here.

**STATUS: CHECKPOINT H20 — awaiting go before H19 (forecast combination).**

---

## CHECKPOINT H19 — combination: **numbers MET, mechanism NOT SUPPORTED**

`src/nowcast/combo.py` + `tests/test_combo.py`. Reporting layer only; no frozen config, no primary
instrument, no ledger row touched.

### Weight selection — all three took the PRE-COMMITTED path (the stability check fired)

| instrument | fold w's (pre-2023) | full-sample w | spread | decision |
|---|---|--:|--:|---|
| cpi_headline | 1.00, 1.00, 1.00, 0.57 | 0.74 | **0.43** | **precommitted w=0.25** (spread > 0.25) |
| cpi_core | 0.00, 0.17, 0.75, 0.00 | 0.06 | **0.75** | **precommitted w=0.25** |
| pce_core | — (n=0 pre-2023) | — | — | **precommitted w=0.25** (sample too small) |

The pre-registered fallback did exactly its job. Note the headline folds wanted **w≈1.0** (our call
dominated Cleveland pre-2023) and the full-sample estimate was 0.74 — so **w=0.25 is markedly *less*
favourable to us than the estimation data suggested.** The results below are achieved under a
conservative weight, not a flattering one.

### Head-to-head on consensus months (pp)

| instrument | n | ours | consensus | **combo(ours,consensus)** | vs consensus | vs ours |
|---|--:|--:|--:|--:|--:|--:|
| cpi_headline | 30 | 0.0727 | 0.0733 | **0.0633** | **−0.0100** | −0.0094 |
| cpi_core | 27 | 0.0853 | 0.0529 | **0.0505** | −0.0024 | −0.0348 |
| pce_core | 9 | 0.0770 | 0.0367 | **0.0316** | −0.0051 | −0.0454 |

**Numerical expectations MET:** headline combo beats consensus alone (−0.0100 pp); core ties/marginally
better (−0.0024, within noise); PCE better (−0.0051). **No dramatic win → no audit triggered.**

### But the pre-registered MECHANISM is NOT SUPPORTED — and that is the honest headline

The expectation attributed the headline gain to *"orthogonal energy information"*. Two diagnostics say
otherwise:

1. **Error correlations are only moderate** — headline **+0.497**, core +0.458, PCE +0.177 — and the
   blended error sd is below both inputs in every case (headline 0.0838 vs ours 0.1063 / consensus
   0.0898). That is the textbook **Bates–Granger diversification** result: combining two imperfectly
   correlated forecasts reduces error *mechanically*, with no new information required.
2. **The gain is NOT concentrated where the claimed mechanism lives.** Splitting headline months by
   gasoline contribution: combo-vs-consensus is **−0.0110 pp in high-gasoline months** and
   **−0.0090 pp in low-gasoline months** — essentially identical. If orthogonal energy timing were the
   source, the gain would concentrate in high-gasoline months. It does not.

**Verdict: the combination gain is real but it is DIVERSIFICATION, not demonstrated orthogonal skill.**
The number came out as predicted; the reason did not. Recorded as such rather than banked as evidence
that our forecast carries unique information.

### A constraint that decides how this can ever be used

**A combo call cannot be made at our freeze.** Consensus closes ~T-1 to T-3 — *after* our T-4 freeze.
So `combo(ours,consensus)` is not a faster product; it is a **later, slightly more accurate** one, and
it forfeits the entire speed advantage that is Instrument A's and the CPI nowcast's actual value
proposition. If it ever joins the ledger as a distinct instrument, its `as_of` must be the **consensus
availability date**, not our freeze — otherwise the row would misrepresent when the call was knowable.

### Admission proposal
**REPORT, do not promote.** Publish `combo(ours,consensus)` as a labelled combination product with the
diversification caveat attached, for the months where consensus exists. Do **not** present it as an
accuracy claim about "ours" (standing labelling rule), and do **not** add it to the ledger until the
as-of/timing question above is settled — it would need its own pre-registration for a forward claim.

**STATUS: CHECKPOINT H19 — awaiting go before TASK 3 (forward vintage capture).**

---

## CHECKPOINT TASK 3 — forward vintage capture → **LIVE**

`_ingest.archive_vintage()` archives an immutable full-history snapshot to
`data/raw/{source}/vintage_{date}/` with a manifest (source, url, retrieved_at, sha256, bytes, rows,
period range, vintage_status, and *why* the snapshot exists). Re-running a pull the same day raises
`VintageExists` rather than overwriting — **idempotent by refusal**, because a replaced snapshot would
destroy exactly the point-in-time evidence the archive exists to preserve.

**Wired and proved on a real pull:** `zori` captured `vintage_2026-07-26` (138 rows,
2015-01 → 2026-06, sha-verified, 1.04 MB), and re-running the same day correctly refused. Also wired:
`atlanta_fed_wage`, `indeed_wage`. `apartment_list` is documented-not-built (JS-gated, no static URL),
so it has no fetch to wire.

`tests/test_vintage_capture.py` — 5 guards: overwrite refused (with the original bytes verified
intact), distinct dates coexist and list in order, the manifest records everything a re-run needs,
**every `revised_latest_only` pipeline actually wires capture** (a non-capturing one is silent data
loss), and the committed zori snapshot still hashes to its manifest.

**The ATRR gap — found while wiring, and it changes what Task 3 delivers.** There is **no ATRR
pipeline, no ATRR raw data, and 0 ATRR rows in the DB**, yet H14's recorded verdict cites specific
ATRR figures. That evaluation ran on a fetch that was never ingested through a naru pipeline —
a **hard-rule-2 violation**. So: H14's numbers are **not currently reproducible from this repo** (the
verdict was a rejection, so nothing is built on top of it), and **capture cannot yet apply to ATRR
because there is nothing to hook into**. The 2027-07 re-evaluation therefore has a stated
precondition: build `pipelines/atrr` first, or no archive accrues. Recorded in the H14 annotation and
the runbook rather than smoothed over.

---

# SPRINT SUMMARY — appended to the closing argument

**Three items, two hypotheses, zero adoptions — and the session's most valuable output is a
correction to my own method plus two precisely-scoped follow-ups.**

**H20 (forward-published factors) — research question YES, aggregate adoption NO.** BLS *does* publish
forward factors (`bls.gov/cpi/seasonal-adjustment/home.htm`: *"Each year with the release of the
January CPI, seasonal adjustment factors are recalculated"*; *"introduced February 13, 2026"*) and we
have ingested them since Session 3A. **At component level they are essentially exact** — 0.0002 pp
versus up to **0.9920 pp** for the prior-year carry on gasoline. That gain **does not survive
aggregation**: `SA0`/`SA0L1E` are indirectly adjusted, so the aggregate factor must be reconstructed
from components at only 64% published-factor coverage, and it pays a partition-replication penalty the
legacy aggregate-implied factor avoids by construction. The gate failed on **condition 3 (2026 holdout:
+0.0206 headline / +0.0394 core)** → **NOT ADOPTED**, frozen configs untouched. Two disclosures: my
first two runs scored against **latest-vintage** SA and reached the *opposite* conclusion — wrong,
because BLS revises SA five years back and the published factor reproduces the **first release**; and
my "January unchanged" assertion was **imprecise rather than violated** (both arms fall back, to
different quantities), with an explicit leakage audit confirming **0** current-year factor rows usable
at any of five Januaries' freezes. **H21 is flagged, not started:** apply published factors at the
*component* level inside the forecast path, plus fix the benchmark's actual-target from latest-vintage
to **first-release** (they differ by 0.0480 pp mean / 0.2201 pp max against a ~0.073 pp head-to-head
MAE) — pre-registered with the warning that **our numbers may get worse**, since the current
conversion is aligned to the easier target.

**H19 (forecast combination) — numbers met, mechanism not supported.** All three instruments took the
**pre-committed w = 0.25** because the fold-stability check fired (headline spread 0.43, core 0.75, PCE
n=0) — and note the headline folds wanted w≈1.0, so the weight used is *less* favourable to us than the
estimation data implied. `combo(ours,consensus)` beat consensus alone on all three
(headline 0.0633 vs 0.0733 pp; core 0.0505 vs 0.0529; PCE 0.0316 vs 0.0367). But the pre-registered
*mechanism* — orthogonal energy information — is **falsified**: error correlations are only moderate
(+0.50/+0.46/+0.18) with blended sd below both inputs, i.e. textbook **Bates–Granger diversification**,
and the headline gain is **flat across the gasoline split** (−0.0110 high vs −0.0090 low) where the
claimed mechanism would concentrate it. **The gain is diversification, not demonstrated skill.** And a
constraint decides its use: consensus closes *after* our T-4 freeze, so a combo call **forfeits the
entire speed advantage** that is the system's actual value proposition — it is later and slightly more
accurate, not faster. **REPORTED, not promoted**; never a claim about "ours"; no ledger entry until the
as-of/timing question gets its own pre-registration.

**Task 3 (forward vintage capture) — LIVE**, and it converts a permanent blocker into a dated one:
H14's revision contamination becomes re-runnable on our own archive from **2027-07**, *provided*
`pipelines/atrr` gets built — which this session discovered was never done, and said so.

**The through-line, unchanged and now better-evidenced:** every improvement attempt this program has
made since Session 7 has failed for a *specific, named, structural* reason rather than for want of
effort — access, evidence, vintage integrity, indirect-aggregation reconstruction, or
diversification-mistaken-for-skill. The floor is real. What moved this session was **measurement
quality**: we now know exactly where the SA-conversion error lives (component-exact factors, lost in
aggregation) and exactly which target the benchmark should have been scoring against.

**STATUS: SPRINT COMPLETE. Nothing adopted; frozen configs untouched; ledger untouched.**
