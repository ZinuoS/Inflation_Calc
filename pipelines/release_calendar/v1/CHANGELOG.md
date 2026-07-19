# Changelog — release_calendar

## v1 — 2026-07-19

Initial. Source: FRED `fred/release/dates` for release_ids 10 (CPI), 46 (PPI),
50 (Employment Situation), 54 (PCE / Personal Income & Outlays), realtime
1990-01-01 → 9999-12-31 (history + future scheduled). Edge fetcher (../fetch.py)
resolves dedup/mapping and emits the canonical CSV; this artifact loads it via
naru's CSV source reader.

- reference_period = release_month − 1 for CPI/PPI/Employment; PCE marked
  `provisional_pending_vintage` (BEA P&O month-boundary slippage — timebase.py
  reassigns from ALFRED first-release vintages, Task 3).
- release time imposed at 08:30 ET (convention); override table empty pending
  spot-check.
- Collisions resolved earliest-wins; collisions + gaps (incl. real 1995-96 and
  2025 shutdown anomalies) logged to ../data/raw/.../exceptions.json.
