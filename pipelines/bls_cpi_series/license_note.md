# License note — bls_cpi_series (BLS CPI component series, SA + NSA)

Reviewed: 2026-07-19.

**Source.** U.S. Bureau of Labor Statistics — CPI public time-series flat files,
US-city-average component files: `https://download.bls.gov/pub/time.series/cu/`
(cu.data.1.AllItems, cu.data.2.Summaries, cu.data.11–18, cu.data.20).

**Terms.** U.S. Government work, public domain. BLS public data flat files are
published for bulk download; we fetch each file once per run with an identified
User-Agent, well under human-browsing intensity. No auth wall, no CAPTCHA. robots.txt
of download.bls.gov permits /pub/time.series/. Attribution to BLS retained in provenance.

**Vintage status.** `official_current` (a Group-C category): the CURRENT published
history of each official CPI series, SA and NSA. FOR METHODOLOGY REPLICATION (Sessions
3A/3B) ONLY — NEVER a backtest target. Backtest targets stay on ALFRED first-release
vintages via timebase (rule 6). These current values are restated and must not be
regressed as first-release.
