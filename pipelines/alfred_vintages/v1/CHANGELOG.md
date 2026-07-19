# Changelog — alfred_vintages

## v1 — 2026-07-19

Initial. Point-in-time vintages from ALFRED (FRED observations, full realtime span)
for 19 series (CPI/PPI/PCE targets + major CPI components). Edge fetcher
(../fetch.py) stacks all series into one CSV; this artifact loads it via naru's CSV
reader into the bitemporal `observations` table.

- Key (series_id, reference_period, observed_asof_vintage): distinct value per
  vintage; no vintage supersedes another.
- Data finding: raw BLS major-group ids (CUSR0000SAF, ...) are NOT in ALFRED; used
  FRED alias ids (CPIFABSL, CPIHOSSL, ...) which are archived. mapping_series_id
  records the mapping.yaml crosswalk.
- Missing (".") observations dropped at the edge; vintage_end kept as string
  (open vintages carry 9999-12-31, beyond pandas Timestamp range).
- first_release view (earliest observed_asof_vintage per series+reference_period)
  materialized after load by src/nowcast/views.py.
