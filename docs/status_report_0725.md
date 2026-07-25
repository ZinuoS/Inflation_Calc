# Status report — nowcast accuracy by sector, with confidence ranges

**As of 2026-07-25.** Historical out-of-sample backtest, **n=88 CPI prints (2019-01 → 2026-06)**, all
calls generated at the **T-3 freeze** from frozen admitted configs (`config/component_models.yaml`),
nothing refit. Companion notebook: `notebooks/nb06_prediction_status.ipynb`.

**Live forward calls are NOT graded in this report.** Ledger entries #1 (CPI 2026-07) and #2 (PCE
2026-06) are standing predictions; PCE adjudicates **2026-07-30**, CPI **2026-08-12**. This report is
backtest evidence only — it is what the confidence ranges below are built from.

**Units.** Primary figures are in **percentage points (pp)** — the release convention (BLS/BEA publish
to one decimal, so **one published increment = 0.1 pp**). Basis points appear alongside for the
sector decomposition, where pp values get small. **1 pp = 100 bp.**

---

## 1. Aggregate accuracy and confidence range

| instrument | n | MAE (pp) | MAE (bp) | bias (pp) | 80% confidence range (pp) |
|---|--:|--:|--:|--:|---|
| **CPI headline NSA MoM** | 88 | **0.115** | 11.5 | −0.053 | **[−0.26, +0.09]** |
| **CPI core NSA MoM** | 88 | **0.126** | 12.6 | −0.057 | **[−0.29, +0.10]** |
| **PCE core (Instrument A)** | 40 | **0.080** | 8.0 | +0.004 | **[−0.12, +0.13]** |

**YoY note (release context, never a target).** Both agencies publish MoM *and* YoY. YoY is excluded
from every error statistic here by **CLAUDE.md rule 8** (overlapping 12-month windows autocorrelate
the error series and inflate apparent skill). Where a YoY figure is useful it is derived
mechanically — eleven of twelve months are already published, so a single MoM call *determines* it and
inherits exactly its uncertainty (see `docs/pce_status_report.md`). **MoM is the scored quantity.**

Reading in the **published convention** (prints are released to 0.1 pp = 10 bp): the CPI headline MAE
is **≈1.1 published increments**, and the 80% range spans roughly **−2.6 to +1 increments**. The PCE
bridge is tighter (**0.8 increments**) and essentially unbiased.

**Both CPI instruments carry a negative bias (≈−5 bp): the system under-predicts slightly on
average.** That is a real, reportable property, not noise — it persists across 88 prints.

## 2. Sector-level backtest error — the core of this report

Each sector's own NSA MoM, forecast at T-3 and compared to the official major-group print. **MAE and
the 80% range are in the sector's own units** (a sector with 2.5% weight moving 100 bp contributes
only ~2.5 bp to the aggregate).

| sector | CPI weight | MAE (pp) | MAE (bp) | bias (bp) | 80% range (bp) | n |
|---|--:|--:|--:|--:|---|--:|
| Housing | 43.8% | **0.128** | 12.8 | -5.8 | [-32, +11] | 88 |
| Transportation | 16.6% | **0.450** | 45.0 | -4.0 | [-84, +59] | 88 |
| Food & beverages | 15.0% | **0.201** | 20.1 | -8.0 | [-45, +19] | 88 |
| Medical care | 8.5% | **0.221** | 22.1 | +0.0 | [-32, +33] | 88 |
| Education & communication | 6.1% | **0.208** | 20.8 | -6.8 | [-38, +26] | 88 |
| Recreation | 4.7% | **0.306** | 30.6 | -9.7 | [-65, +35] | 88 |
| Other goods & services | 2.9% | **0.271** | 27.1 | -10.9 | [-52, +30] | 88 |
| Apparel | 2.5% | **0.771** | 77.1 | -6.4 | [-116, +113] | 88 |

**How to read this.** Two very different things drive the ranking:

- **Transportation (45 bp MAE)** — high error, and it *matters* (16.6% weight). This is gasoline
  volatility; it is also where our only strong admitted proxy lives (EIA weekly, R² 0.978), so the
  error is *already* as low as public weekly data allows.
- **Apparel (77 bp MAE)** — the **worst** sector by far, but at 2.5% weight it contributes little.
  Apparel is high-variance, heavily promotional, and sits in the untrackable-idiosyncratic class.
- **Housing (12.8 bp MAE on 43.8% of weight)** — the **best risk-adjusted sector**. Structurally slow
  by BLS's 6-panel/6-month-ratio design, so the seasonal baseline works well. This single fact is why
  the aggregate MAE is as low as it is.

## 3. Sector contribution to aggregate error — and the cancellation finding

Weight-share × sector error, i.e. how much each sector actually *moves* the headline miss:

| sector | gross \|contribution\| (bp) | signed (bp) |
|---|--:|--:|
| Transportation | 7.57 | -0.87 |
| Housing | 5.61 | -2.54 |
| Food & beverages | 3.02 | -1.21 |
| Apparel | 1.98 | -0.15 |
| Medical care | 1.87 | +0.01 |
| Recreation | 1.41 | -0.42 |
| Education & communication | 1.27 | -0.42 |
| Other goods & services | 0.78 | -0.31 |

| | value |
|---|--:|
| gross sector error (Σ\|contribution\|) | **23.50 bp** |
| net aggregate error | **11.81 bp** |
| **offset ratio** | **2.0×** |

**The aggregate is roughly twice as accurate as its parts, because sector errors partly cancel.** The
independently-measured PCE bridge shows the same structure at **4.0×** (see
`docs/pce_wedge_decomposition.md`). This is now a **general property of the system, measured on both
instruments**, and it carries two honest implications:

1. Part of the headline accuracy is **offsetting**, not per-sector precision. A month in which sector
   errors *align* is materially worse than the average — the observed worst month is **62 bp**.
2. Improving one sector moves the aggregate **less** than its gross contribution implies, and can move
   it in either direction if it is currently cancelling another error. This is why the last two
   improvement sprints (H11–H17) correctly declined to adopt marginal component fixes.

## 4. Confidence-range caveats (read before using the bands)

- The bands are **empirical quantiles of 88 historical errors**, not a fitted predictive
  distribution. They assume the next month resembles the sample.
- The sample **spans regimes** (2019 calm, 2020–21 COVID, 2022 surge, 2025–26 tariff). Post-2023
  headline MAE is **6.7 bp** vs 15.6 bp pre-2023 — the recent-regime band is materially tighter than
  the full-sample band shown above.
- Two months (**2025-10, 2025-11**) have **no print** (appropriations lapse) and are excluded
  throughout — never imputed.
- Seam months (Jan/Feb) carry an extra irreducible **~2.5–2.8 bp** SA-conversion constant (measured,
  H13) that no model change can remove.

## 5. Standing position

| claim | status |
|---|---|
| Replication at the rounding floor (CPI 0.50 bp, PPI-FD 1.93 bp) | **established** |
| Beats AR(1)/seasonal-naive/zero benchmarks ~2× | **established** |
| Energy-timing edge on headline vs Cleveland Fed | **established** |
| Beats later-closing press consensus | **NO — parity on headline, deficit on core** |
| PR-1 side-of-consensus edge | **LIVE, unproven** (75%, n=12, p=0.15) |
| Live forward calls | **2 standing, ungraded** (07-30, 08-12) |
