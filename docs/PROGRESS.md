# PROGRESS — honest status

For a reader who was not in the build sessions. No spin either way: gaps are stated as
plainly as wins. Dates are absolute; "as of" 2026-07-19.

## DONE (with evidence)

- **Leakage firewall + within-vintage MoM** — `src/nowcast/timebase.py`
  (`asof` / `asof_mom` / `asof_mom_for_ref`), the ONLY sanctioned official-side read path.
  MoM is computed within a single vintage. Evidence: at the 2023 BEA PCE re-referencing,
  naive cross-vintage MoM fabricates **−6.97%** for one month vs a true **+0.145%**
  (711 bp of pure look-ahead); the CPI February seasonal restatement injects a recurring
  **3.5 bp** leak. Both are exhibited in `tests/test_vintage_mom.py` and the checkpoint log.
- **vintage_floor** — refuses reference months below a per-series floor where "first
  release" is a bulk-archived restatement (`PreVintageFloor`). It removed 246 restated-as-
  first months from the gasoline reconciliation alone. `series_vintage_floor` view + tests.
- **Adversarial leakage test** — `tests/test_timebase.py`: reading between reference-period
  end and release returns the prior print; exact-release-instant is strictly-before; a
  50-pair property sweep asserts no value is ever returned before its release.
- **Group A + Group C ingestion** — shelter (ZORI), gasoline & heating-oil (EIA via FRED),
  wage monitors (Atlanta Fed, Indeed); official CPI components SA+NSA (**181/181 published
  strata**, 268k rows) and PPI final-demand + PCE-source industry PPIs. All via frozen
  naru pipeline artifacts with provenance + golden parse tests. `official_current` is
  methodology-replication only, never a backtest target.
- **Reconciliation harness** — `src/nowcast/{alignment,reconcile}.py` + `nb02` +
  `docs/reconciliation_report.md`. Every proxy regressed on its official component using
  first-release within-vintage MoM; UNSTABLE flagging; optimism flags; skip / pre_floor /
  insufficient_overlap verdicts.
- **Admission table as it stands** — exactly one stable admissible price proxy at usable
  weight: **EIA gasoline vs the gasoline stratum, R²=0.75, β≈0.8** (pass-through, unrevised).
  Heating-oil weak/coarse; NADAC placeholder unstable; the rest monitor / insufficient.
- **H2 confirmed** — shelter (33% of CPI) is UNSTABLE at R²≈0.01 with sign-flipping betas:
  market-rent indices (ZORI) lead all-tenant CPI rent by ~a year, so they are a *leading*
  indicator, not a contemporaneous next-print feature. (This is the pre-registered result,
  not a failure.)
- **naru gaps filed** — `docs/naru_gaps.md`: #1 non-Excel readers (CSV/TSV shipped), #5
  editable-install shadow, #6 connection lifecycle (WAL/timeout shim), #7 bulk-load O(n²)
  key index, #8 archive-crawl ergonomics.

## PARTIAL

- **Group B (point-in-time archives).** manheim built (point_in_time, 11 months — only
  ~2025 dated files remain hosted); tsa built (6-month demand monitor). cox_atp: the ATP
  extractor is validated but full coverage is blocked on inconsistent report URLs
  (naru#8) — no patchy series shipped. adobe_dpi (UA-gated + patchy), freightos_drewry
  (JS-gated; H4 leads-context-only), opentable (discontinued → vendor_only): documented,
  not built.
- **NADAC** — 5-year matched-model **placeholder** index (2020–2026, geomean-of-relatives),
  marked for the Session-3A weighted-index upgrade; reconciles unstable vs a coarse
  medical-care-commodities official (drugs stratum has no ALFRED vintages).
- **Conditionals skipped (missing key/file):** usda_ams (`USDA_AMS_API_KEY`),
  bea_pce_detail (`BEA_API_KEY`), keepa (`KEEPA_API_KEY`), apartment_list (no CSV; JS-gated,
  ZORI covers shelter). Each has a folder + spec + STATUS/SKIPPED note.

## NOT STARTED

- **Session 3A** — index mathematics (Jevons / Laspeyres / Fisher) + X-13 seasonal
  adjustment engine.
- **Session 3B** — CPI/PPI→PCE bridge engine + two-tier acceptance gate.
- **Session 4** — per-component nowcast models + purged/embargoed walk-forward validation.
- **Session 5** — forward scraped collectors (permissive sources only).
- **Session 6** — event-study backtest + monthly print-report generator.
