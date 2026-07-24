# Pristine forward ledger

**Append-only.** One row per forward call, written when the call is made — before the print.
Legal edits: (1) append a new row, (2) populate `consensus_bp` / `consensus_asof` when the preview
articles land (after our T-4 freeze, before the print), (3) populate `realized_bp` / `deviation_bp`
/ `verdict` once the print lands. Any other change breaks the row's `row_hash` and fails
`tests/test_ledger.py`.

`call_bp` = predicted first-release MoM (NSA for CPI, core PCE for PCE). `band_bp` = the OOS band
at that lead. `consensus_bp` = press consensus median, carrying its OWN as-of (it closes later than
our freeze). `frozen` = whether the call was past its T-4 freeze. Misses are kept, never edited out.


| n | instrument | ref_month | as_of | frozen | call_bp | band_bp | consensus_bp | consensus_asof | realized_bp | deviation_bp | verdict | row_hash |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | cpi | 2026-07-01 | 2026-07-22 | no | -5.1 | 8.8 | — | — | — | — | — | 265f227e5cbb |
| 2 | pce | 2026-06-01 | 2026-07-14 | yes | +7.6 | 8.0 | — | — | — | — | — | ab0165470397 |
