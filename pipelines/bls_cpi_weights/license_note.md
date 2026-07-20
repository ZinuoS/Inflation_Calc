# License note — bls_cpi_weights (BLS CPI relative-importance weights, vintaged)

Reviewed: 2026-07-19.

**Source.** U.S. Bureau of Labor Statistics — CPI relative importance of components,
annual tables `https://www.bls.gov/cpi/tables/relative-importance/{year}.xlsx`.

**Terms.** U.S. Government work, public domain. One fetch per year, identified UA. No
auth wall/CAPTCHA. Attribution to BLS retained in provenance.

**Vintage discipline.** Each {year}.xlsx is the relative importance "as of December
{year}" — the weights in effect during calendar year {year} (BLS updates weights
annually). Ingested with weight_year = {year} so weights.py serves the correct vintage
(a 2021 backtest sees 2021 weights, never today's). Available years at this URL:
2020–2025; earlier years 404 (out of coverage — weights.py refuses them).
