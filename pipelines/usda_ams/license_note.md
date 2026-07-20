# License note — usda_ams (USDA AMS retail food prices)

Reviewed: 2026-07-19.

**Source.** USDA Agricultural Marketing Service (AMS) — retail food price reports
(National Retail Report series: meats, dairy, fruits, vegetables). Public via the AMS
Market News API (`marsapi.ams.usda.gov`) and the AMS "MyMarketNews" portal.

**Terms.** U.S. Government work, public domain. AMS Market News is published for public
use. The MARS API requires a free API key (no key present; see STATUS.md). No auth wall
beyond the API key, no CAPTCHA. Attribution to USDA AMS retained in provenance.

**Vintage status.** `unrevised` (verify at build): AMS retail feature reports are
weekly point-in-time publications; a report for a given week is not retroactively
restated. Reclassify if an audit finds otherwise.
