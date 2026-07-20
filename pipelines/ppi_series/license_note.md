# License note — ppi_series (BLS PPI final-demand + PCE-source industry PPIs)

Reviewed: 2026-07-19.

**Source.** U.S. Bureau of Labor Statistics — Producer Price Index, via the BLS public
API v2 (`https://api.bls.gov/publicAPI/v2/timeseries/data/`). Final-demand commodity
series (WPS*=SA, WPU*=NSA) and the four PCE-source industry PPIs (PCU*): hospitals,
physicians/home-health/nursing (health care), scheduled air transport, portfolio
management, and property/casualty insurance.

**Terms.** U.S. Government work, public domain. BLS public API (keyless tier): batched
requests (<=25 series each), identified User-Agent. No auth wall, no CAPTCHA. Attribution
to BLS retained in provenance.

**Vintage status.** `official_current` — current published PPI history, for methodology
replication + the PCE bridge in 3A/3B ONLY, NEVER a backtest target (targets use ALFRED
vintages via timebase). PPI is restated; these current values must not be regressed as
first-release.
