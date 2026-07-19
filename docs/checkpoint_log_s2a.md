# Session 2A checkpoint log — Release calendar + ALFRED vintages (the leakage firewall)

## Pre-build decisions (approved in-session)

1. **naru gap protocol executed.** naru's runner was Excel-only and its raw registry
   lacked (url, retrieved_at). Logged as naru#1–4 in docs/naru_gaps.md.
2. **naru#1 resolved (hybrid, user-approved):** added CSV/TSV source readers to naru
   (branch `feat/csv-tsv-source-reader`, commit 35a2612, local/unpushed; naru suite
   464 green). Delimited sources now load through naru's governed path directly.
   JSON (ALFRED) still normalized to CSV at the edge.
3. **Firewall source (user-approved):** FRED `fred/release/dates` for release dates
   (deterministic, 36y, +future scheduled), release TIME imposed by BLS/BEA 08:30 ET
   convention with a documented override table; not the BLS/BEA HTML archives.
4. **Provenance shim (naru#2):** edge fetcher writes provenance.json (url REDACTED of
   api_key, retrieved_at_utc, sha256, http_status, bytes); a repo-side
   meta_fetch_provenance table will join to naru's raw_files by hash.

## CHECKPOINT 1 — release_calendar (Task 1)  ·  BUILT & LOADED

Reference-period decision (approved): month−1 for CPI/PPI/Employment now; PCE marked
`provisional_pending_vintage`; timebase.py reassigns all reference_periods from ALFRED
first-release vintages in Task 2–3.

**Built:** edge fetcher (`fetch.py`), naru artifact (`v1/`, source_format: csv),
loaded into `data/db/nowcast.sqlite` (run_id=1, **1691 rows**, all 8 validations PASS,
1691 lineage rows). Provenance shim (`src/nowcast/provenance.py`, naru#2) links every
row → CSV hash → upstream FRED URL + retrieval time (custody chain verified).
Offline tests green (`tests/test_release_calendar.py`).

Rows per print in DB: CPI 442, Employment 443, PPI 441, PCE 365 (PCE lower = month-1
gaps/collisions collapsed; corrected via vintages in Task 3). Ref range 1989-12 → 2026-11.

**Time spot-check (done):** BLS CPI schedule page confirms **08:30 AM ET** for 3 recent
prints (Dec-18-2025, Jan-13-2026, Feb-13-2026); matches the imposed convention exactly.
Evidence saved to data/raw/.../bls_cpi_schedule_spotcheck.html. Override table stays empty.

### Original CHECKPOINT 1 detail (retained)

Fetched 2026-07-19, raw JSON + provenance in
`data/raw/release_calendar/2026-07-19/` (gitignored; provenance.json has redacted URLs).

### Coverage (fred/release/dates, realtime 1990-01-01 → 9999-12-31)

| print | raw dates | range | future scheduled |
|---|---|---|---|
| CPI | 463 | 1990-01-18 → 2026-12-10 | 5 |
| PPI | 463 | 1990-01-12 → 2026-12-15 | 5 |
| Employment Situation | 451 | 1990-01-05 → 2026-12-04 | 5 |
| PCE (Personal Income & Outlays) | 456 | 1990-01-29 → 2026-12-23 | 6 |

Far exceeds the ≥10y target (36 years).

### Reference-period mapping — the finding that needs your call

Reference period assigned as release_month − 1 (monthly prints, ~1-month lag),
earliest-date-wins on collision, all collisions/gaps logged to `exceptions.json`.

- **CPI / PPI / Employment: clean.** Collisions (CPI 21, PPI 19, Emp 8) are the annual
  February seasonal-factor re-releases — earliest-wins keeps the true first release.
  Gaps (CPI 2, PPI 3, Emp 1) are **real schedule anomalies, correctly caught**: the
  1995-96 and 2025 U.S. government shutdowns (e.g., CPI Oct-2025 missing, Dec-1995
  delayed). These are logged, not smoothed — exactly per doctrine.
- **PCE: month−1 arithmetic is unreliable (82 collisions, 79 gaps).** BEA P&O releases
  land at month-end and frequently slip across the calendar boundary to the 1st–3rd,
  so a fixed offset misassigns ~18% of months. Plus the 2018-19 shutdown catch-up
  (two March-2019 releases). The release DATES are correct; only the reference-month
  *assignment by arithmetic* is fragile.

**Decision needed** (see chat): how to assign PCE (and generally) reference_period —
authoritative correction from ALFRED first-release vintages (Task 2), a self-contained
sequential heuristic, or reverse the task order. release_calendar's firewall value
(release datetime per date) is solid regardless; only the reference_period join is at issue.

### Release time
Imposed 08:30 ET for all rows (release_time_basis = convention_0830ET); override table
empty pending spot-check. Spot-check vs BLS for 3 recent prints to be done before freeze.

### Not yet built (blocked on the decision)
naru artifact (v1/), the load into nowcast.sqlite, meta_fetch_provenance table,
golden fixture, validations (one-per-print-per-ref-month; CPI precedes PCE).
