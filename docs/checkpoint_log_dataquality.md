# Checkpoint log — Data-quality sprint (H12–H15)

Four bounded, pre-registered improvements to already-understood strata. No new estimators, no new
hypotheses beyond these four. Frozen configs untouched **except** where a pre-registration explicitly
supersedes — **H13 only**, and only if it passes its gate. Live ledger rows are never touched;
adopted improvements re-run the BACKTEST, not the two frozen forward calls.

**PRE-REGISTERED IN FULL BEFORE ANY BUILD (this section written first).** Access facts checked
2026-07-25: keys present = FRED, BEA (USDA_AMS, KEEPA **absent**); frozen-config guard green;
AAA + GasBuddy robots reachable; x13as binary present at X13PATH.

---

## H12 — daily gasoline replaces weekly at the freeze

**Build.** Ingest AAA daily national retail regular gasoline (license note first; publication block
`daily, observed ~same-day`). **Fallback:** GasBuddy national daily if AAA archive access fails rule
5 — document whichever is used and why. History as deep as the source honestly provides (no
back-filling beyond what it publishes). Reconcile daily→monthly NSA vs SETB01 NSA. Then re-run the
gasoline component (`SETB01`) with **daily-through-T-3** information replacing **weekly-as-of-T-3**,
through the existing firewall (`proxy_timebase` + H8 window), frozen β unchanged.

**Pre-registered expectation.** Gain is **concentrated** in (a) months where `|gasoline NSA MoM| >
300 bp` and (b) months with an **end-of-month price move the weekly series missed** (weekly EIA is a
Monday snapshot; the last ~week of the month can move after the final weekly read). **Near-zero
elsewhere.** Deliverable is the **month-by-month delta table**, not just the average.

**Adoption gate (proposal; Ash decides).** Adopt the daily feed for SETB01 only if the SETB01-level
MAE improves on the high-move / end-of-month subset **and** is unchanged (|Δ| < ~0.3 bp) elsewhere.
This changes the *feed*, not the model (β stays frozen; it is a data-quality swap, not a new estimator).

**Red flag → audit.** A gain in low-move, no-end-of-month-move months (where the weekly snapshot
already saw everything) would mean the delta is noise or a firewall slip — audit before adoption.

---

## H13 — factor-revision model (may SUPERSEDE the raw prior-year February factor)

**Build.** For each stratum, predict its **February seasonal-factor revision** by running our X-13 on
the latest **unrevised NSA through December**, vintage-faithfully (December-vintage information only —
no peeking at the Jan/Feb release that introduces the new factors). Compare **predicted vs realized**
factor revisions over the **last 8 Februaries**.

**Pre-registered expectation.** Seam-month (Jan/Feb annual-seam) MoM **error reduction** for the four
floor-audited strata (SEHE01, SETB01, SEFH, SETB02 — the least-reliable-seasonal set) **and** the
headline/core aggregate. **ZERO effect outside seam months — asserted as a test:** a non-seam change
means a bug (the factor-revision model must be inert where there is no factor revision).

**Adoption gate (proposal; Ash decides).** Supersede the raw prior-year February factor **only if**
seam MAE improves **AND** non-seam MAE is unchanged, on the standard OOS window, labelled
**QUASI-OOS** (the 8 Februaries overlap the eval window). This is the ONLY hypothesis permitted to
touch a frozen config (`factors.py` February path), and only on passing.

**Red flag → audit.** Any non-seam movement, or a seam gain larger than the known seam error itself
(44–130 bp, the irreducible annual-seam calendar fact) — either is a bug or leakage.

---

## H14 — BLS all-tenant research series (ATRR) informs the rent/OER carry

**Build.** Ingest the BLS all-tenant regressed-rent research series (`official_current` or
`point_in_time` per its **actual** publication practice — verify before choosing; quarterly cadence in
the publication block). Reconcile + `lead_scan` vs **SEHA** (rent) and **SEHC01** (OER) at quarterly
alignment. If the lead is **stable**, wire an ATRR-informed carry for rent/OER (estimated pre-2023
where history permits, frozen), evaluated on the standard window.

**Pre-registered expectation.** **Modest** MAE reduction on the two rent strata (SEHA, SEHC01) — they
are the highest-weight, most-panel-smoothed components, where a research series with an earlier read
could help a little. Anything **dramatic** triggers the audit (rent is structurally slow by the
6-panel/6-month-ratio design; a large gain would contradict Session-7's finding and imply leakage).

**Adoption gate (proposal; Ash decides).** Adopt only if the lead is stable in the fold-selection
sense (not a single-window artifact) and the OOS MAE improves modestly on the two strata with
near-zero effect elsewhere.

---

## H15 — completeness (two independent sub-items)

**(a) USDA AMS.** `USDA_AMS_API_KEY` is **ABSENT** (verified 2026-07-25) → **SKIPPED**, recorded again
as a standing gap (build per the existing spec + reconciliation vs SAF11 only if the key appears). No
fabrication, no forward-only collector.

**(b) PPI-FD aggregator.** Build the PPI final-demand aggregator: published **FD component weights** +
component series through `index_math`, with a **replication check vs official FD MoM**. Target:
**rounding-floor territory** (like the CPI replication, ~0.5 bp). Replace the `oos_report_1.md`
NOT-BUILT entry with the **measured** replication number. This is a measurement/replication task, not
a predictive model — no admission decision, just the number.

**Red flag.** If FD replication is far from the floor (say > 5 bp), that is itself the finding
(missing components / wrong weight vintage) — reported honestly, not tuned away.

---

## CARRY-ITEM (from the runbook flag) — ledger key extension

Extend `ledger.append_call`'s dedup key from `(instrument, ref_month)` to
`(instrument, ref_month, freeze_kind)`, where `freeze_kind` is derived from the existing `frozen`
flag (`frozen`/`prefreeze`) — **no schema migration, no hash change** (the hash already covers `as_of`
+ `frozen`, which differ between the T-21 and T-3 rows). Add a test covering the **Aug-9 case**: a
prefreeze `cpi 2026-07` row and a frozen `cpi 2026-07` row coexist with distinct valid hashes;
re-appending the frozen row is idempotent. Makes the Aug-9 T-3 freeze pure execution. Not a
hypothesis — a mechanical unblock, done outside the H-checkpoints.

---

**STATUS: PRE-REGISTRATION COMPLETE. Proceeding to the carry-item, then H12 → CHECKPOINT H12, wait.**

---

## CHECKPOINT H12 — daily gasoline → **CANNOT BUILD (no admissible source)**

Both the primary and the pre-registered fallback are closed under CLAUDE.md rule 5; neither is fought.

| source | daily retail history | status |
|---|---|---|
| **AAA** (primary) | endpoint is `gasprices.aaa.com/wp-admin/admin-ajax.php` | **BLOCKED** — `/wp-admin/` is `Disallow`ed in AAA robots.txt. The allowed page shows only today/week/month/year-ago snapshots, not a series. |
| **GasBuddy** (fallback) | `charts.gasbuddy.com/ch.gaschart?...Period=18` | **BLOCKED** — returns a **GIF chart image** (670×325), not numeric data. Extracting values = OCR/screenshot workaround (rule 5 forbids). Retail prices are also GasBuddy proprietary commercial data. |
| EIA / FRED | — | no daily retail series exists (EIA retail is weekly, already ingested as SETB01's proxy; 0 daily-retail hits on FRED). |

**Verdict.** H12 is **not buildable at current source access.** The pre-registered expectation
(gain concentrated in `|gasoline MoM| > 300 bp` and end-of-month moves the weekly snapshot missed)
is **untestable** without a licensed daily-retail feed — recorded as a gap, not fabricated. Not
claimed: that daily retail *would* fail to help; it is **untested, not disproven** (reopens if a
licensed AAA/OPIS daily feed is ever purchased). The weekly EIA series stays SETB01's proxy,
unchanged. No pipeline built (rule 5: a source without an admissible, licensed path gets none).

**Admission proposal:** none — nothing to admit. Weekly gasoline feed stands.

**STATUS: CHECKPOINT H12 — awaiting go before H13 (factor-revision model).**

---

## CHECKPOINT H13 — factor-revision model → **NOT SUPPORTED (rejected; frozen config UNTOUCHED)**

**Feasibility.** X-13 runs vintage-faithfully (NSA through Dec Y-1). statsmodels does not surface
X-13's projected next-year factors → drove `x13as` directly with `forecast{maxlead=12}` +
`x11{appendfcst=yes save=(d16)}` (logged as a naru gap; shim lived in the eval only, not promoted).

**Result vs pre-registered expectation (EXPECTED seam MAE reduction).** The opposite: X-13 projection
is **~4× worse** than the carry-forward baseline at predicting BLS's realized February factor, on
**every** code (pooled seam SA-MoM factor error **29.9 bp baseline → 120.9 bp H13**; per-code table
below). SETB02: carry-forward is **exact** (0.0 bp) — impossible to beat.

| code | baseline (carry-fwd) | H13 (X-13) | | code | baseline | H13 |
|---|--:|--:|---|---|--:|--:|
| SETB01 | 25.9 | 56.2 | | SETB02 | 0.0 | 162.7 |
| SEHE01 | 54.8 | 273.5 | | SA0 (headline) | 2.8 | 8.1 |
| SEFH | 98.8 | 236.5 | | SA0L1E (core) | 2.5 | 8.6 |

**Why.** BLS seasonal factors are stable year-to-year (carry-forward is a strong baseline), and our
X-13 config ≠ BLS's (different ARIMA/outlier/filter choices) — so the projection substitutes *our*
factor instead of predicting *theirs*. At the aggregate the seam error carry-forward leaves is
already tiny (~2.5–2.8 bp); there was little to win and the projection lost badly.

**Non-seam assertion (pre-registered):** HOLDS by construction — H13 replaces only the February
factor, so every non-Feb month is identical under both; delta = 0 exactly. No bug (a non-seam change
would have implied one).

**Adoption gate:** FAILS the first condition (seam MAE must improve — it worsens 4×). **Frozen config
`factors.py` February path is NOT touched** — verified untouched by git. The carry-forward prior-year
factor stands. Pre-registered non-win; the gate did exactly its job of protecting the frozen path.

**Admission proposal:** REJECT. No config change.

**STATUS: CHECKPOINT H13 — awaiting go before H14 (BLS ATRR → rent/OER carry).**

---

## CHECKPOINT H14 — ATRR-informed rent/OER carry → **NOT ADOPTED (audit-blocked: revision contamination)**

**Publication practice VERIFIED (pre-registration required this before classifying).** The source
relocated to `bls.gov/cpi/research-series/r-cpi-ntr.htm`. BLS states R-CPI-ATR is **"perpetually
revised, with recent periods being prone to large revisions"** → classification is
**`revised_latest_only`**, NOT `point_in_time`/`official_current` (the default assumption was wrong;
verification overturned it). Quarterly cadence, published ~mid-month after quarter-end (observed:
2024q1→2024-04-17, q2→07-15, q3→10-17, q4→2025-01-21, 2025q1→04-16). **Publication is currently
PAUSED** ("lapse in appropriations") — the same shutdown behind our 2025-10/11 CPI gaps. History
1999q4–2025q3 (104 quarters). Published change columns are **4-quarter (YoY)** → unusable as targets
per hard rule 8; quarterly changes derived from the index level instead.

**The lead is real and stable.** Quarterly-change lead scan peaks at **lag-1 quarter**: SEHA
**+0.859**, SEHC01 **+0.841**, with clean decay either side. Stable across all four sub-periods
(SEHA +0.70/+0.83/+0.58/+0.90; SEHC01 +0.52/+0.83/+0.51/+0.91), betas positive throughout — it
passes the pre-registered stability bar.

**Measured gain, and why it does not survive.** A 50/50 ATRR-informed carry at the freeze gave
SEHA **11.04 → 8.41 bp (−2.63)** and SEHC01 **10.24 → 8.21 bp (−2.03)** over n=82. That is a ~20–24%
reduction on ~33% of CPI weight — **"dramatic", which the pre-registration says triggers the audit
before adoption.** Audit, three tests:

1. **Publication-lag firewall: CLEAN.** 90 months checked, **0 violations** — prior-quarter ATRR is
   always public before the freeze.
2. **Lead vs level: the signal is REAL.** Replacing ATRR with its own full-sample constant makes
   things *worse* (SEHA 13.19, SEHC01 12.61 bp) — so the gain is the time-varying signal, not a level
   shift. H14's mechanism is genuine.
3. **REVISION CONTAMINATION: DISQUALIFYING.** The backtest fed each month the *current* (revised)
   prior-quarter value. Comparing per-quarter vintage files against the latest:

   | quarter | quarterly change AS PUBLISHED | latest vintage | revision |
   |---|--:|--:|--:|
   | 2024q2 | **−18 bp** | **+106 bp** | **124 bp (sign flip)** |
   | 2024q4 | +65 bp | +77 bp | 12 bp |
   | 2025q1 | +95 bp | +71 bp | 24 bp |

   The signal the −2.6 bp gain rests on **largely did not exist at the freeze** (2024q2 flipped sign).
   BLS publishes **no ATRR vintage archive**, so a leakage-free backtest is **not constructible** from
   available data.

**Verdict.** **NOT ADOPTED.** The lead is real, stable, and mechanism-anchored, but the measured gain
is contaminated by revisions unavailable at forecast time, and the vintage history needed to measure
it honestly does not exist. Adopting on a revised-data backtest would be exactly the leakage this
project's firewall exists to prevent. Frozen configs untouched; no carry wired; no pipeline built
(rule 6: an unvintaged source cannot support a backtest claim).

**Recorded, not claimed:** ATRR is **untested-honestly, not disproven** — it reopens if BLS ever
publishes an ATRR vintage archive (or if forward-captured `observed_asof` snapshots accumulate from
today, which is a *forward-only collector* and out of scope this session by instruction). This also
independently **corroborates Session 7's H2/design finding**: market-rent-style signals lead CPI rent,
but the usable-at-freeze portion is far smaller than the revised-data correlation suggests.

**Admission proposal:** REJECT (no config change). Retain as a documented reopening condition.

### H14 ANNOTATION — forward vintage capture (added 2026-07-26, Task 3)

**Re-runnability, honestly qualified.** Task 3 makes `revised_latest_only` sources archive an
immutable full-history snapshot on every pull (`data/raw/{source}/vintage_{date}/` + manifest;
`_ingest.archive_vintage`, immutability asserted by `tests/test_vintage_capture.py`). Once ~4 quarters
of snapshots exist, a revision-contaminated backtest becomes **pristinely re-runnable on our own
archive** — each month reads the value we actually held, not today's restated one. **Calendar entry:
re-evaluate H14 in 2027-07** (see `docs/runbook.md`).

**CORRECTION (2026-07-26) — two earlier claims in this repo were WRONG, and both are now fixed.**

1. **"BLS publishes no ATRR vintage archive" — FALSE.** BLS publishes **dated per-quarter archive
   files** (`r-cpi-ntr-and-r-cpi-atr-{YYYY}q{N}.xlsx`, **2023q3 → 2025q3**) alongside the current
   workbook. Verified as genuine as-published snapshots, two ways: reference quarter 1999q4 reads
   **102.2753677** in the 2024q2 file versus **102.388** in the current one; and the ATR row count
   increments by **exactly one per quarter** (97, 98, 99 … 104), which is what a growing
   as-published series must do. The earlier statement was an assumption I never checked.
2. **"H14's numbers are not reproducible from this repo" — NO LONGER TRUE.** `pipelines/atrr` now
   exists and has **backfilled all 9 BLS vintages** into `data/raw/atrr/vintage_{tag}/`, immutable
   with manifests. H14's contamination evidence is **reproduced from our own archive**: the 2024q2
   quarterly change reads **−17.6 bp as published** (vintage_2024q2) versus **+106.3 bp in the latest
   vintage** — a **+123.9 bp revision**, matching the "−18 → +106" originally recorded. The
   hard-rule-2 gap (ATRR analysed from a fetch that was never ingested) is **closed**: 104 quarterly
   rows are now in `proxy_observations` and every vintage is on disk.

**What this changes about the re-evaluation.** H14 no longer needs four quarters of our own snapshots —
**BLS's archive already spans 2023q4 → 2025q3 (8 usable vintages)**, so a pristine re-run is possible
**now**, bounded by that window rather than by 2027. It is **not run here**: re-opening a recorded
verdict requires its own pre-registration. The 2027-07 calendar entry is retained but **re-scoped** —
it is no longer a precondition-blocked wait, just the point by which our own snapshots extend the
window past BLS's archive start.

**Publication is PAUSED** (cited verbatim from the source page): *"Due to a lapse in appropriations
resulting in uncollected CPI Housing Survey data for October 2025 and competing priorities, BLS paused
publication of the R-CPI-NTR and R-CPI-ATR data in April 2026."* Latest data = **2025q3**. Our current
pull was therefore **byte-identical to vintage_2025q3 and correctly skipped** by the archive's
content-hash dedupe — for a paused source, "no new vintage" is the honest signal, not a storage task.

**Capture status:** live for **atrr** (9 vintages), **zori** (`vintage_2026-07-26`, 138 rows,
sha-verified), **atlanta_fed_wage**, **indeed_wage**. `apartment_list` stays documented-not-built
(JS-gated, no static URL), so it has no fetch to wire.

**STATUS: CHECKPOINT H14 — awaiting go before H15 (a: USDA if key; b: PPI-FD aggregator).**

---

## CHECKPOINT H15 — completeness

### H15(a) USDA AMS → **SKIPPED (key absent, again)**
`USDA_AMS_API_KEY` absent from `.env` and unset in the live environment (verified 2026-07-25). Per the
pre-registration: no build, no fabrication, no forward-only collector. Standing gap, recorded for the
third session running. Reconciliation vs SAF11 remains available the moment a key exists.

### H15(b) PPI final-demand aggregator → **BUILT, replication at the floor**

**Weights sourced.** Published FD-ID relative importances (`bls.gov/web/ppi/ppi-fdgrouprel.xlsx`,
Dec-2024 weights, posted 2026-06-11) yield a **complete non-overlapping 33-group leaf partition
summing to exactly 100.000** — the coarsest-complete-partition doctrine reused from the CPI side. The
33 NSA `WPUFD…` leaf series were retrieved from the BLS public API (two batches: 25-series/request
cap; 10-year history cap without a registration key → window starts 2017-02).

| PPI FD replication (NSA MoM), via price-updated Laspeyres | value |
|---|--:|
| MAE 2017-02 → 2025-12 (n=107) | **3.89 bp** |
| **MAE 2023+ (n=36)** | **1.93 bp** |
| median / p90 / max | 2.47 / 8.43 / 29.45 bp |
| partition coverage | 100.0% of FD weight |

**vs pre-registered target ("rounding-floor territory, like CPI"): MET.** 2023+ at **1.93 bp** sits at
the floor, mirroring the CPI headline result (0.50 bp NSA). Residual concentrates in the **2022 energy
spike** (2022-07 +29.5, 2022-06 −20.3 bp) — the **weight-vintage era effect** (Dec-2024 weights cannot
reproduce 2022 relative importances), the identical signature the CPI replication showed pre-2023, not
a machinery fault. The red-flag threshold (>5 bp ⇒ missing components/wrong weights) is **not** tripped
on the modern window.

**`oos_report_1.md` NOT-BUILT entry replaced by the measured number.** Measurement/replication only —
**no forward PPI skill claimed or measured**, so no admission decision applies; this closes a
replication gap, not an accuracy gap.

**STATUS: CHECKPOINT H15 — awaiting go before FINAL (tables, sprint summary, commit).**

---

# SPRINT SUMMARY — the accuracy program's closing argument

**Four hypotheses, pre-registered in full before any code ran. Zero adopted. One gap closed.**

| H | target | verdict | binding reason |
|---|---|---|---|
| **H12** | daily gasoline replaces weekly at the freeze | **CANNOT BUILD** | **Access.** AAA's history sits under a robots-`Disallow`ed path; GasBuddy publishes its national history as a proprietary chart *image*. No daily retail series exists on EIA/FRED. Untested, not disproven — reopens with a licensed feed (OPIS noted, not pursued). |
| **H13** | predict the February factor revision (X-13 on Dec-vintage NSA) | **NOT SUPPORTED** | **Evidence.** ~4× worse than carry-forward at predicting BLS's realized factor (pooled seam error 29.9 → 120.9 bp), on every code. Mechanism: BLS factor drift is small, carry-forward near-optimal (SETB02 exactly right). Frozen `factors.py` untouched. |
| **H14** | ATRR-informed rent/OER carry | **NOT ADOPTED** | **Vintage integrity.** The lead is real and stable (lag-1 quarter, SEHA +0.86 / OER +0.84, stable across 4 sub-periods) and the −2.6/−2.0 bp gain is a genuine time-varying signal — but it is measured on **revised** data. ATRR is "perpetually revised"; the 2024q2 quarterly change went **−18 bp as published → +106 bp revised**. No vintage archive exists, so a leakage-free backtest is not constructible. |
| **H15a** | USDA AMS | **SKIPPED** | Key absent (third session running). |
| **H15b** | PPI-FD aggregator + replication | **BUILT, AT THE FLOOR** | 33-group leaf partition summing to 100.000; **MAE 1.93 bp (2023+)**, 3.89 bp full window, 100% weight coverage. Replaces the `oos_report_1.md` NOT-BUILT entry. Replication only — no forward PPI skill claimed. |

**Nothing was adopted, so PR-1 and PR-2 are NOT recomputed** — the backtest is unchanged, and the two
live ledger rows (CPI 2026-07, PCE 2026-06) stand frozen and untouched, as they must. The only
evaluation-doc changes are annotations: the seam constant (H13) and the H12 closure.

## Why this reads as a closing argument

Three sessions of improvement attempts have now failed for **three structurally different reasons**,
and none of them is effort-limited:

- **Session 7 (services acquisition):** four sources, zero admissible — access, observability,
  information-ordering.
- **H11 (sampling-aware baseline):** rejected on its own audit; only 22% of the apparent gain was the
  pre-registered mechanism.
- **This sprint:** access (H12), evidence (H13), vintage integrity (H14).

The pattern is not "we ran out of ideas." Each failure identified a **specific, named boundary**:
freely-accessible public price data is fully harvested; BLS's own published factors are too stable to
out-predict; and research series that *do* lead CPI are revised too heavily to use honestly at a
freeze. Two of the three boundaries are **licensing/vintage-archive** limits — firm-side problems, not
research problems.

What survived the whole program is therefore a **bounded, measured, honest system**: replication at
the rounding floor on both CPI (0.50 bp headline NSA) and now PPI final demand (1.93 bp, 2023+); a
stratum-level trackability map that says which 40.7% of CPI weight is *not* nowcastable with public
data and why; an energy-timing edge on headline versus the Cleveland Fed; parity-to-modest-deficit
versus later-closing consensus; and no core edge — claimed nowhere.

**The floor is real, it is measured, and it has now been attacked from four independent directions
without moving.** That — not a win rate — is the program's result. The remaining live question is
narrow and already ticking: **PR-1**, the side-of-consensus claim, powered only by forward prints at
~1/month on a public append-only ledger. Everything else that could change the numbers is gated on
data we cannot legitimately obtain, which is exactly why the program closes here rather than
continuing to spend effort against a documented wall.

**STATUS: SPRINT COMPLETE. Nothing adopted; nothing frozen was touched; ledger untouched.**
