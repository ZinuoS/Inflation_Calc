# License note — eia_gasoline (EIA weekly retail gasoline)

Reviewed: 2026-07-19.

**Source.** U.S. Energy Information Administration (EIA) weekly U.S. Regular All
Formulations retail gasoline price, delivered via the FRED API series `GASREGW`
(FRED redistributes the EIA series). `https://api.stlouisfed.org/fred/series/observations?series_id=GASREGW`.

**Underlying data origin.** EIA Gasoline and Diesel Fuel Update survey — a U.S.
Government work, public domain. FRED redistribution is governed by the FRED API
Terms of Use (attribution to FRED retained in provenance rows).

**Terms.** FRED API Terms (reviewed 2026-07-19); one request per run, identified
User-Agent, API key from env `FRED_API_KEY` (never hardcoded, REDACTED in stored
URLs). No auth wall, no CAPTCHA. robots.txt N/A (documented public API).

**Vintage status.** `unrevised` — EIA publishes each weekly retail price as final;
these weekly survey values are not subsequently restated. (If EIA ever restates, the
classification would move to point_in_time via the EIA archive; not needed now.)

**Depth.** GASREGW begins 1990-08 (deeper than the plan's assumed 1993 — actual depth
recorded in mapping.yaml, not padded).

**Backup.** Direct EIA API / EIA weekly CSV if FRED access changes.
