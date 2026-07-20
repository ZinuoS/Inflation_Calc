# License note — cox_atp (Cox Automotive / KBB New-Vehicle Average Transaction Price)

Reviewed: 2026-07-19.

**Source.** Cox Automotive / Kelley Blue Book — New-Vehicle Average Transaction Price
(ATP), published as dated monthly "insights" press releases:
`https://www.coxautoinc.com/insights/{month}-{year}-atp-report/`.

**Terms.** Press releases published for public reference. Under D1 we ingest a single
DERIVED number (the headline ATP) and publish derived indices/methodology only — never
redistribute Cox's article text. Golden fixture is SYNTHETIC (not Cox's page). Attribution
retained in provenance. One fetch per report, identified UA. No auth wall/CAPTCHA.

**Vintage status.** `point_in_time` — each monthly report is the ATP as published that
month (first release).

**COVERAGE BARRIER (documented, not hidden — see STATUS.md).** The deterministic value
extraction WORKS (anchor: first $XX,XXX after "New-Vehicle Average Transaction Price"),
but the report URL slugs are INCONSISTENT month-to-month (Jun/May-2026 resolve;
Apr/Mar/Jan-2026 404 under this pattern — they exist under other slugs). Clean consecutive
coverage needs an insights-index/sitemap crawl (naru#8 archive-crawl gap), not URL
enumeration. Not shipped as a patchy non-consecutive series (never interpolate).
