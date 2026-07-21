# Changelog — seasonal_factors_loader

## v1 — 2026-07-20
Loads BLS published PROJECTED CPI-U seasonal factors (long form: series_id, item_code,
reference_period, projected_factor, factor_year, published_asof) into
`bls_seasonal_factors`, keyed by (series_id, reference_period). Source = the annual
"Seasonal factors table, YYYY" XLSX (2021–2026 machine-readable; pre-2021 PDF-only and
robots-disallowed, so out of scope). `projected_factor` is a ratio (published pct/100),
`factor_year` coerced to int. `published_asof` = the Jan-YYYY CPI release date (factor
introduction), the vintage key used by `src/nowcast/factors.py` to keep the factor
knowable-before-the-month. Powers the Checkpoint-2 reroute: NSA / projected_factor = SA.
