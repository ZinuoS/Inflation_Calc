# License note — atlanta_fed_wage (Atlanta Fed Wage Growth Tracker)

Reviewed: 2026-07-19.

**Source.** Federal Reserve Bank of Atlanta — Wage Growth Tracker, Unweighted Median
Hourly Wage Growth (Overall), via FRED `FRBATLWGTUMHWGO`.
`https://api.stlouisfed.org/fred/series/observations?series_id=FRBATLWGTUMHWGO`

**Underlying origin.** Atlanta Fed (a Federal Reserve Bank), computed from Census/BLS
CPS microdata. Redistributed by FRED under FRED API Terms (reviewed 2026-07-19). One
request/run, identified UA, key from env (REDACTED in stored URLs). No auth wall/CAPTCHA.

**Role.** MONITOR source for Services less energy services (cost-pressure signal), per
mapping.yaml/research plan — NOT a next-print price proxy. It is a wage-growth RATE,
not a price level; reconciliation treats it as monitor-only.

**Vintage status.** `revised_latest_only` — the tracker is restated as the underlying
CPS panel and weights update; no point-in-time archive. Amendment 2 optimism flag applies.

**Depth.** FRBATLWGTUMHWGO begins 1997-01 (matches plan).
