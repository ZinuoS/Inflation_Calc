# Changelog — cpi_weights_loader
## v1 — 2026-07-19
Loads vintaged BLS relative-importance weights (weight_year, item_code, cpi_u, cpi_w)
into cpi_weights. Served as-of a date by src/nowcast/weights.py (a 2019 backtest sees
2019 weights). weight_year coerced to int, so the naru transform emits it numeric.
