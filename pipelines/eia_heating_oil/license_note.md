# License note — eia_heating_oil (EIA No.2 heating oil, NY Harbor spot)

Reviewed: 2026-07-19.

**Source.** EIA No. 2 Heating Oil Prices, New York Harbor (daily spot), via FRED
`DHOILNYH`. `https://api.stlouisfed.org/fred/series/observations?series_id=DHOILNYH`.

**Underlying origin.** EIA — U.S. Government work, public domain; FRED redistribution
under FRED API Terms (reviewed 2026-07-19). One request/run, identified UA, key from
env, REDACTED in stored URLs. No auth wall/CAPTCHA.

**Vintage status.** `unrevised` — daily spot quotes are published final.

**IMPORTANT proxy caveat.** This is a WHOLESALE SPOT price (NY Harbor), not the
residential RETAIL heating-oil price the CPI "Fuel oil" stratum measures. It is a
weak proxy (pass-through + regional). Recorded so reconciliation treats it with
suspicion. CPI Fuel oil weight is only 0.083, so this is low-priority. Backup: EIA
residential heating oil weekly retail series if a stronger proxy is needed.

**Depth.** DHOILNYH begins 1986-06 (deeper than plan's 1990).
