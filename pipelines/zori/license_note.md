# License note — zori (Zillow Observed Rent Index)

Reviewed: 2026-07-19.

**Source.** Zillow Research public data — Zillow Observed Rent Index (ZORI),
smoothed, seasonally adjusted, metro + US national:
`https://files.zillowstatic.com/research/public_csvs/zori/Metro_zori_uc_sfrcondomfr_sm_sa_month.csv`

**Terms (reviewed 2026-07-19).** Zillow Research aggregate data is published for free
download and non-personal use such as real-estate market analysis, with required
attribution. Zillow's terms: derivative works of the Aggregate Data may be displayed
and distributed "only so long as the Zillow Companies are cited as a source on every
page where the Aggregate Data are displayed, including 'Data Provided by Zillow Group.'"
We honor this: any published index or chart derived from ZORI will carry
"Data Provided by Zillow Group." Under research-plan D1 we publish indices/methodology
only, never redistribute Zillow's raw micro-data.

**robots.txt.** The data files are served from `files.zillowstatic.com` (a static file
host), NOT the UA-gated `www.zillow.com` application. The download path is a published
public CSV intended for download; we fetch a single file per run with an identified
User-Agent, well under any human-browsing intensity. www.zillow.com/robots.txt
restricts `/research/monthly-reports/` for general crawlers, which we do not access.
No auth wall, no CAPTCHA.

**Vintage status.** `revised_latest_only` — ZORI is a repeat-rent index that is
restated as the panel updates (the history downloaded today is not the history that
was published in real time). No point-in-time archive is offered. Per Amendment 2,
every reconciliation stat computed from ZORI is annotated "optimistic: proxy vintage
unavailable."

**Backup.** BLS New Tenant Rent Index (public, quarterly, 2005+) and Apartment List
(separate pipeline) if ZORI access changes.
