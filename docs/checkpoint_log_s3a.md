# Session 3A checkpoint log — index math + seasonal adjustment

## TASK 0 — carry-questions · CHECKPOINT 0

### 0a — C1–C3 conditional builds
`USDA_AMS_API_KEY`, `BEA_API_KEY`, `KEEPA_API_KEY` all still **ABSENT** from `.env`.
usda_ams / bea_pce_detail / keepa remain **SKIPPED** (folders + specs + STATUS notes
stand). No builds this session; their placeholder indices stay out of Task 4 scope
until a key lands.

### 0b — Manheim restatement verification → UNREVISED, historical ingested
Compared the point-in-time archive (11 dated files, Jan–Nov 2025, each file's newest row =
that month's first release) against the same months in the latest full download:
**all 11 months matched EXACTLY (diff 0.0000).** Methodology confirms the only historical
"recalculation" was the one-time 1995→1997 rebasing; "revised" = full-month superseding the
preliminary mid-month, not restatement of published full-month values.

→ MUVVI full-month is **unrevised**. Ingested the full **1997–2025 (347 months)** history
as `vintage_status: unrevised`, superseding the 11 point-in-time rows (values identical).
Evidence + residual caveat (2025-only exact-match window; annual SA revision of pre-2025
history not positively excluded) cited in `pipelines/manheim/license_note.md`.

**H1 no longer overlap-starved.** Reconciliation Manheim vs SETA02 (used cars),
first-release: contemporaneous **n=177, R²=0.015, unstable, NOT optimism-flagged**. That
low contemporaneous R² is the honest LEAD structure, not a defect — a lead-correlation
sanity check confirms it (and validates the pipeline is not buggy):

| lead k (months) | n | corr | R² |
|---|--:|--:|--:|
| 0 (contemporaneous) | 177 | +0.122 | 0.015 |
| 1 | 177 | +0.394 | 0.155 |
| **2** | 177 | **+0.592** | **0.350** |
| 3 | 177 | +0.435 | 0.190 |

Manheim wholesale leads CPI used-car retail by ~2 months (peak R²=0.35) — real H1 signal,
to be exploited as a LEAD in Session 4, not admitted as a contemporaneous next-print feature
(same shape as ZORI/shelter H2, but a stronger, cleaner lead).

### Task-3 preflight (heads-up, not blocking now)
`x13as` binary is **NOT on PATH**. Task 3 (X-13ARIMA-SEATS) will STOP for its install per
the prompt; flagging now so it can be installed during review. macOS install step will be
given at Task 3.

56 tests green.
