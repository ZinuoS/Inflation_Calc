# Checkpoint log — PCE wedge decomposition + closure sprint (H16–H17)

Pre-CPI daily retry is OUT OF SCOPE (Keepa-gated, standing). Live ledger rows untouched; no
adjudication before 2026-07-30; frozen configs untouched except via H16's adoption gate. Residue
specs are NOT touched. Nothing is fitted to 2.4.4U errors.

**PRE-REGISTERED IN FULL BEFORE ANY BUILD (this section written first).**

---

## Verified publication facts (cited, checked 2026-07-25)

BEA Personal Income & Outlays / **Underlying Detail tables** are published as
**"Annual, Quarterly, and Monthly estimates"** on the Personal Income & Outlays release cycle
(`https://www.bea.gov/data/consumer-spending/main`: "Current release: June 25, 2026 / Next release:
July 30, 2026"). Cross-checked against our own `release_calendar`: PCE reference month M releases at
**M+1, day ~25–30** (observed 2025-11→2026-11: +34 to +60 days, median ≈ +55).

**Ingested reality:** `bea_pce_detail` RC (nominal) rows are **monthly**, 2010-01 → 2026-05
(74,860 rows). So monthly composition *is* available historically — the open question is what was
knowable **at each historical CPI-day**, not whether the data exists now.

**The binding constraint (drives H16's whole design).** `official_current` has **no `observed_asof`
column**, so the firewall cannot be enforced row-wise; it must be enforced by the **publication-lag
rule**: 2.4.5U for reference month M becomes public at the PCE release for M (~M+1 day 25–30).
Instrument A calls month M on **CPI-day (~M+1, day 10–13)** — which is **BEFORE** that release.
Therefore at CPI-day for month M the freshest *knowable* nominal detail is for reference month
**M−1** (published ~M, day 25–30), **not** M. H16 must respect exactly this. A run that uses month-M
shares to forecast month M is look-ahead and is disqualified, not reported as a win.

---

## H16 — weight-vintage freshness

**Build.** Add a `publication` block to `pipelines/bea_pce_detail/spec.yaml` recording the verified
cadence/lag above (currently the block says "annual … knowable far ahead", which is true for the
*annual* path but silent on monthly). Then rebuild the bridge weight path to use the **freshest
shares knowable at each historical CPI-day** — i.e. trailing shares through reference month **M−1**
— replacing the current **prior-calendar-year annual** shares (`bea_weights(ref_year)` →
prior-year annual mean). Two runs are produced and both retained: **STALE** (current, prior-year
annual) and **FRESH** (knowable-at-CPI-day trailing). Residue specs untouched; component mappings
untouched; only the weight vector changes.

**Pre-registered expectation.** MAE improvement **concentrated in fast-composition-shift eras**
(2021–22 reopening/energy, 2025–26 tariff), **small elsewhere** (composition shares are slow-moving,
so most months should barely differ). Era split is a required deliverable, not optional.

**Adoption gate (all three must hold; Ash decides).**
1. standard-window MAE **improves**, AND
2. mean **signed** bias stays **≤ 1 bp** in absolute value, AND
3. **no era degrades by > 0.5 bp**.

**Red flag → audit before adoption.** A large gain in *slow*-composition eras (where shares barely
move, so there is nothing to win) ⇒ the delta is noise or a firewall slip. Any use of month-M shares
for month M ⇒ look-ahead, disqualified outright.

**Scope note.** H16 is the ONLY item permitted to touch the frozen weight path, and only on passing
all three gate conditions.

---

## H17 — wedge decomposition (MEASUREMENT, not modeling)

**Build.** For the standard window, decompose Instrument A's monthly error into three additive parts:

1. **weight-vintage component** — the fresh-vs-stale difference, taken directly from H16's two runs
   (this is why H16 runs first, whether or not it adopts).
2. **mapping component** — per-component tracking error vs **2.4.4U actuals** (`*RG` price indexes),
   weight-summed, with **residue lines separated out** and reported separately (never blended into
   the trackable total).
3. **irreducible remainder** — total error minus (1) minus (2), reported as what neither weights nor
   component mapping explains.

**Deliverable.** `docs/pce_wedge_decomposition.md` with the three numbers and a **per-component
league table of |mapping error| × weight** — the top of that table **is** the priority list for any
future mapping audit. For the **worst 5 non-residue** components: one paragraph each,
**handbook-checked** — is the mapping plausibly **incomplete** (H9a-style fixable) or
**concept-divergent** (a floor)? **Citations or it is labelled a guess.** No remapping this session;
findings feed a pre-registered **H18** only if the table justifies one.

**Pre-registered expectation.** The three parts sum (by construction) to the total; the **mapping
component dominates** (Session-R2 already located ~7 bp of structural floor in commodity-flow
derivation, and the ranked diagnosis put ~5 service components at ~15% of weight driving the
dispersion). Weight-vintage should be **small** (slow shares). If instead weight-vintage dominates,
that contradicts H16's own expectation and triggers a consistency check rather than a claim.

**Not a modeling exercise.** Nothing is fitted to the 2.4.4U errors (explicit DO-NOT). The league
table is descriptive attribution only; no coefficient is estimated from it, this session or by
implication.

---

**STATUS: PRE-REGISTRATION COMPLETE. Proceeding to H16 → CHECKPOINT H16, wait.**

---

## CHECKPOINT H16 — weight-vintage freshness → **NOT ADOPTED (clean pre-registered NULL)**

**Publication block added** to `pipelines/bea_pce_detail/spec.yaml` recording the verified monthly
cadence, the `lag_days: 55` rule, and the firewall note (Instrument A calls month M on CPI-day,
which precedes the PCE release for M ⇒ freshest knowable detail is **M−1**; `official_current` has no
`observed_asof`, so this lag rule *is* the firewall).

**Two arms, weight vector the only difference.** STALE = current frozen path (prior-calendar-year
annual shares). FRESH = trailing-12 nominal shares through **M−1** (firewall-respecting; no month-M
shares were used to forecast month M — the look-ahead disqualifier was avoided by construction).

| | MAE | mean signed |
|---|--:|--:|
| STALE (frozen path) | **7.97 bp** | +0.36 bp |
| FRESH (knowable-at-CPI-day) | 7.99 bp | +0.43 bp |
| **delta** | **+0.01 bp** | +0.07 bp |

**Era split (required deliverable):**

| era | n | stale | fresh | delta |
|---|--:|--:|--:|--:|
| 2023 (normalizing) | 12 | 8.74 | 8.83 | +0.09 bp |
| 2024 (calm) | 12 | 7.90 | 7.85 | **−0.05 bp** |
| **2025–26 (tariff)** | 16 | 7.45 | 7.46 | **+0.00 bp** |

**Verdict vs expectation: the expectation FAILED, and the null is informative.** The pre-registration
predicted gains concentrated in fast-composition-shift eras — the 2025–26 tariff era delta is
**+0.00 bp**, and the only (trivially) favourable era is the *calm* one. Adoption gate condition 1
(standard-window MAE improves) is **not met** (+0.01 bp worse), so the gate fails; conditions 2 and 3
are moot.

**Sanity check — the null is real, not a no-op.** The two weight vectors genuinely differ (nominal
levels 1.9–3.3% apart; largest share shifts +0.17 pp in 2023-06, +0.06 pp in 2025-06, +0.11 pp in
2026-05). **Mean |share shift| is only 0.02–0.04 pp.** That is the mechanism: PCE expenditure
composition moves far too slowly, even across a tariff regime, for weight freshness to move a MoM
price aggregate. The original frozen design note ("annual expenditure shares barely move … bias
direction is negligible") is now **empirically confirmed** rather than assumed.

**Frozen weight path NOT touched.** Prior-year annual shares stand.

**Admission proposal:** REJECT (no config change). The measured fresh-vs-stale difference (+0.01 bp
overall, ±0.09 bp by era) is carried forward as H17's **weight-vintage component** — the null is
exactly the input H17 needs.

**STATUS: CHECKPOINT H16 — awaiting go before H17 (wedge decomposition).**

---

## H17 — method correction (recorded, not hidden)

The first decomposition pass summed **absolute** per-component contributions and produced an
**impossible negative remainder** (total 7.97 − wv 0.18 − mapping|.| 23.77 − residue|.| 8.00 =
**−23.97 bp**). The bug was mine and it is methodological, not numerical: **|a| + |b| ≠ |a + b|**, so
an additive identity cannot be built from magnitudes. The pre-registration's "the three parts sum by
construction" only holds for **signed** contributions.

Rerun with signed contributions. Both views are then reported, because they answer different
questions and the gap between them is itself the finding:
- **signed** — satisfies the additive identity; gives the honest three-way split.
- **gross (Σ|contribution|)** — magnitude of component error before offsetting; the ranking metric
  for the league table.

**The gap is the headline result.** Gross component error (~31.8 bp/month across non-residue +
residue) is **~4× the net error (7.97 bp)**. The bridge's accuracy is therefore *not* "small errors
everywhere" — it is **large per-component errors that substantially cancel**. That reframes the ~7-8 bp
floor: part of it is offsetting luck, and a month in which the component errors align would be
materially worse than the average. (Consistent with the observed max |error| of 24.5 bp.)

---

## CHECKPOINT H17 — wedge decomposition → **DELIVERED** (`docs/pce_wedge_decomposition.md`)

**Signed identity holds** (`total = mapping + residue + weight-vintage + remainder`), n=40:

| part | mean signed | mean \|.\| | gross Σ\|comp\| | variance share |
|---|--:|--:|--:|--:|
| total | +0.36 bp | 7.97 bp | — | 100% |
| mapping (non-residue) | −0.17 | 7.56 | **23.77** | **82.2%** |
| residue (separate) | −3.72 | 4.83 | 8.00 | −3.3% |
| weight-vintage | +0.073 | **0.178** | — | **0.2%** |
| remainder | +4.17 | 6.86 | — | 23.4% |

**Pre-registered expectation CONFIRMED:** mapping dominates (82.2% of error variance), weight-vintage
negligible (0.2%) — independently consistent with H16's null. Mapping is ~130× the weight term.

**Headline finding — the floor is a cancellation equilibrium.** Gross component error **31.77 bp/mo**
collapses to a **7.97 bp** net miss: a **4.0× offset ratio**. The bridge is accurate because large
per-component errors cancel, not because components track well. Therefore (a) the ~7–8 bp floor
contains offsetting luck (max observed 24.5 bp when errors align), and (b) fixing one component moves
net error less than its gross contribution — possibly in the wrong direction.

**Reporting convention (per instruction): both.** MAE 7.97 bp = **0.0797 pp** = **0.80× one published
0.1pp increment**; 40% of months inside half an increment, 68% inside one, 5% ≥ two. Rounded-print
hit-rates are kept as a distinct statistic, never averaged with the MAE. (A pp/bp unit slip in an
interim calculation was caught and corrected: 1 pp = 100 bp.)

**League table + 5 handbook-checked paragraphs** delivered, all citations verbatim from NIPA Handbook
ch.5 Tables 5.A/5.B (retrieved 2026-07-25). Verdicts: air transport **concept-divergent/floor**
(mapping verified correct — the largest gross contributor is *not* a bug); recreational goods
**partly incomplete** (missing telephone-hardware leg; nine-series fixed-weight set vs our five
aggregates); portfolio **incomplete/fixable** (missing PPI investment-advice leg, now priced at
2.60 bp); hospitals **concept-divergent/floor** *plus a stale-note correction flagged* ("out-of-pocket"
appears nowhere in ch.5, so our scope note is unverified); motor-vehicle services **misassigned/fixable**
(SETE insurance belongs to a separate NIPA line deflated by PPI private passenger auto insurance, on a
net-premium concept).

**H18: NOT opened.** Three fixable mappings are priced (2.70 + 2.60 + 1.37 bp gross), which would
justify one in scope — but the offset finding requires any H18 to pre-register that net MAE may be
**unchanged or worse**, and to be judged on per-component tracking error vs 2.4.4U rather than
aggregate MAE. Ash's call.

**STATUS: CHECKPOINT H17 — awaiting go before FINAL (sprint paragraph, commit, push before 07-30).**
