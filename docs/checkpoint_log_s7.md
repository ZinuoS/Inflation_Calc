# Checkpoint log — Session 7 (sampling audit → services acquisition → integration)

## Task 0 — June-2026 postmortem appended, strata flagged

Appended to `docs/prints/2026-06_cpi_DRYRUN.md`. Diagnosis: **gasoline was accurate**
(−926 forecast vs −968 actual = +1.3 bp of the 42.4 bp miss). The miss is a **no-proxy
seasonal-baseline blind spot**: SETE +8.8, SEED03 +5.3, SEHB02 +4.2, SEHF01 +4.1,
OER +2.9, rent +1.8 bp (~35 of 42.4 bp attributed). Flagged as acquisition targets:
**SETE, SEED03, SEHB02, SEHF01**.

---

## CHECKPOINT A — sampling audit

### A1 `mapping/sampling.yaml` — coverage

**181/181 strata**, every field either CITED to the BLS Handbook of Methods (CPI chapter,
retrieved 2026-07-23) or explicitly marked UNVERIFIED. No folklore.

| collection_frequency | n | basis |
|---|--:|---|
| `monthly_big3_bimonthly_elsewhere` | 120 | HOM: monthly in NY/LA/Chicago, **bimonthly elsewhere** (odd/even month assignment) |
| `monthly_all_areas` | 59 | HOM: "Food at home, energy, and selected other items are priced monthly" |
| `housing_panel_6` | 2 | HOM: "six panels ... priced twice per year"; monthly index from **6-month rent ratios** |

Cited: collection frequency, housing panel structure, quality-adjustment methods (incl.
hedonic regression). **Marked UNVERIFIED** (HOM is silent, so not asserted): per-stratum
intra-month collection window; which strata are hedonically adjusted; motor-vehicle-insurance
premium-following methodology (lives in a separate BLS factsheet, not the HOM chapter).

Computed (not cited): `seasonal_reliability_bp` for all 181 — mean across calendar months of
the same-month NSA MoM std-dev, 2014+. Mean 120 bp. Least reliable: SEHE01 555, SETB01 491,
SEFH 446. Most reliable: SEHB01 12, **SEHC01 13, SEHA 14** — the panel-smoothed shelter items.

### A2 `docs/trackability_map.md`

| class | n | CPI weight | floor rationale |
|---|--:|--:|---|
| structurally-slow | 22 | **51.5%** | design/administrative smoothing; the seasonal-AR fallback is the *right* tool |
| untrackable-idiosyncratic | 150 | **32.9%** | high dispersion, no candidate source — the fat-tail generator |
| proxy-plausible | 7 | **9.8%** | named candidate exists (Part B target list) |
| proxy-admitted | 2 | **5.8%** | gasoline (R² 0.978) + used cars — today's edge |

**June movers, in units of their own dispersion σ:**

- **SETE** insurance −1.7σ — **partly a sampling artifact**: bimonthly outside the big-3 means
  a filed-rate change is collected over two months, so a print can be catch-up.
- **SEED03** wireless **−4.4σ** — genuine idiosyncratic repricing, *not* design. And because BLS
  **quality-adjusts** wireless, a posted-price tracker would likely have missed it.
- **SEHB02** lodging −1.3σ — ordinary variance for a stratum whose seasonal fallback is
  structurally weak (σ = 224 bp); a weekly proxy should help materially.
- **SEHF01** electricity ~2σ over-predicted — genuine; EIA-861M is official but ~2-month lag ⇒
  trajectory, not next-print.
- **SEHC01 / SEHA** ~0.8σ / ~1.5σ — small per-unit errors on 33% of weight, on the
  6-panel/6-month-ratio design. **H11 target.**

**Consequence, recorded before Part B is built:** acquisition buys *tail reduction on ~10% of
weight*, not a transformation of the mean — and the wireless case says pre-register the hedonic
caveat rather than assume a tracker solves it.

### A3 — H11 PRE-REGISTRATION (written before any fitting)

**H11 — sampling-aware seasonal fallback.** The current default baseline (`seasonal_ar`,
8-year same-month mean + AR(1)) is uniform across strata. A1 establishes that the sampling
design is *not* uniform, so the baseline is misspecified in two documented ways:

1. **Panel strata (SEHA, SEHC01):** the published monthly change is a weighted average of
   **6-month rent ratios**, one panel per month ⇒ the series is a mechanically induced moving
   average. Longer AR memory should dominate an 8-year same-month mean.
2. **Bimonthly strata (120 of 181):** a shock outside NY/LA/Chicago enters over **two**
   consecutive prints ⇒ own-lag-1 MoM carries signal that a same-month mean discards.

**Pre-registered expectation (the non-win is a legitimate result):**
- Headline OOS MAE gain **≤ 1.5 bp** — modest.
- Gain **concentrated** in SEHC01 + SEHA (each ≥ ~1 bp per-stratum MAE), and modest in
  bimonthly strata.
- **≈ zero** (|Δ| < 0.5 bp) in `monthly_all_areas` strata — the design predicts no mechanism there.

**Pre-registered falsification / red flags** (trigger a leakage audit *before* any admission):
- gain concentrated in `monthly_all_areas` strata, where the design predicts nothing;
- headline MAE improvement **> 3 bp** — too large for a baseline re-specification;
- any gain that disappears when the memory length is swept (must be a curve, not a point).

**Method (binding, per ash-ml-doctrine):** same purged embargoed walk-forward (embargo 2 mo,
min-train 48), fit train-only inside folds, first-release targets, shutdown months skipped.
Memory length swept as a **curve**, not tuned to a winner. Decomposition before verdict.
**Scope: baseline only — no proxies** (that is Part B). Evaluated in a **shadow config**;
`config/component_models.yaml` is not edited unless and until H11 is admitted.

---

**CHECKPOINT A — cleared 2026-07-23.**

---

## CHECKPOINT S1 — lodging (SEHB02, wt 1.07) → **NO ADMISSIBLE SOURCE**

**Primary (STR / CoStar): BLOCKED.** `str.com` and `www.costar.com` return Akamai
`Access Denied` on **`/robots.txt` itself** — the door is shut before any terms can even be
read. Per CLAUDE.md hard rule 5 a blocked source is replaced by its backup, **not fought**: no
retry, no UA rotation, no third-party republication of the same proprietary data.

**Backup 1 — PPI Hotels & Motels ex-casino (`PCU721110721110`, FRED, 2003-12→): REJECTED on
evidence.** Two independent failures:

| test | result |
|---|---|
| lead scan vs CPI SEHB02 NSA MoM (2014+, n=148) | lag −2 **0.00**, lag −1 **0.10**, **lag 0 0.46**, lag +1 0.36 — peak is *contemporaneous*; **no lead** |
| explanatory power | R² 0.21; residual sd **350 bp** vs raw CPI sd **394 bp** — an 11% sd reduction |
| release timing | PPI ref-month *M* lands **+1 to +5 days after** CPI ref-month *M* (checked 8 recent prints; once −1) — **not available at the T-4 freeze** |

Either failure alone disqualifies it. Compare the admitted bar: gasoline R² 0.978, used-cars 0.35.

**Backup 2 — TSA throughput (demand): NOT EVALUABLE.** Only **6 monthly rows** in the DB. The
`pipelines/tsa/license_note.md` already records the standing decision (2026-07-19) that deeper
history "is NOT chased via archives," and that TSA is **monitor-only, never a price proxy**. That
decision is not reversed to serve a new want.

**Verdict.** SEHB02 **reclassified `proxy-plausible` → `untrackable-idiosyncratic`**. Lodging is
not nowcastable at CPI-day with public data. The June-2026 lodging contribution (+4.2 bp) is
**conceded as irreducible** at current source access.

**Not claimed:** that STR *would* have failed. STR is weekly transacted ADR — a different measure
from the PPI survey, and its value is **untested, not disproven** (same standing as H6/Keepa). If
a licensed STR/CoStar feed is ever purchased, S1 reopens.

**Reusable structural finding (binding on S3 and beyond):** because PPI publishes *after* CPI for
the same reference month, **no PPI series can ever be a CPI next-print feature.** PPI *is*
available before the PCE print (~2 weeks later), so it remains legitimate for the PCE bridge —
where it is already used — but it is permanently out of scope as a CPI proxy.

**CHECKPOINT S1 — cleared 2026-07-23.**

---

## CHECKPOINT S2 — wireless (SEED03, wt 1.34) → **NO ADMISSIBLE SOURCE**

The A2 hedonic caveat was **pre-registered and is now CONFIRMED**. This is a stronger result than
S1: the obstacle is not access, it is that *the thing we want to predict is not externally observable.*

**Evidence — CPI wireless vs PPI wireless (`PCU517312517312`), 2014+, n=150.** Two independent
measurements of the price of wireless service, one consumer-side (hedonically adjusted), one
producer-side:

| test | result |
|---|---|
| monthly co-movement | corr **+0.076** — effectively **zero** |
| lead scan | lag −2 −0.02, lag −1 +0.19, lag 0 +0.08, lag +1 +0.09 |
| 12-year cumulative drift | CPI **−23.2%** vs PPI **−25.7%** — wedge only +2.6 pp |
| **June-2026, the target event** | CPI **−331 bp** while PPI was **+1 bp** |

The two series agree almost perfectly on the *decade* and not at all on the *month*. The −331 bp
print left **no trace whatsoever** in the producer-side measure. A posted-plan tracker measures
sticker prices — the same family of thing PPI measures — so the June event is precisely the kind
of move it would have missed.

**Access status (recorded, though moot).** `verizon.com` and `att.com` `robots.txt` **permit** the
plan pages (only carts/availability endpoints disallowed); `t-mobile.com` returns **403** on
robots.txt and is treated as blocked, not fought. So a 2-of-3-carrier tracker was *buildable* —
and is still rejected, on evidence rather than on access.

**Second, independent disqualifier.** A scraper started today has **zero backtest history**. Under
purged embargoed walk-forward it could not be validated for years, and Wayback-style archive
reconstruction of dynamic pricing pages is exactly the archive-chasing declined at S1/TSA.

**Not chased:** lag −1 corr +0.19 is the largest point in the scan, but it is a **post-hoc pick
from a 4-point scan** (~2.3σ at n=150) and was **not pre-registered**. It is recorded and dropped.

**Verdict.** SEED03 **reclassified `proxy-plausible` → `untrackable-idiosyncratic`**. June's
+5.3 bp wireless contribution is **conceded as irreducible** — and, unlike lodging, conceded on
the stronger ground that no external source *can* carry it.

**Running total:** S1+S2 concede **9.5 bp of the 42.4 bp June miss** as structurally irreducible.
`proxy-plausible` has fallen 9.8% → **7.3%** of CPI weight; `untrackable` has risen to **35.4%**.

**STATUS: CHECKPOINT S2 — awaiting go before S3 (motor-vehicle insurance → SETE).**
