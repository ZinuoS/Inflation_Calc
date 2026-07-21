# License / access note — bls_seasonal_factors

**Source:** U.S. Bureau of Labor Statistics, CPI Seasonal Adjustment Tables —
"Seasonal factors table, YYYY (XLSX)".
Index page: https://www.bls.gov/cpi/tables/seasonal-adjustment/
File pattern: https://www.bls.gov/cpi/tables/seasonal-adjustment/seasonal-factors-{year}.xlsx

**Checked:** 2026-07-20.

**Copyright:** Work of the U.S. federal government; not subject to copyright in the United
States (17 U.S.C. §105). Public domain. BLS asks that BLS be cited as the source.

**robots.txt (www.bls.gov, `User-agent: *`, retrieved 2026-07-20):** the seasonal-adjustment
table path is NOT disallowed. The relevant `Disallow` entries are `/scripts`, `/crs`,
`/_private`, `/iisadmin`, `/srchadm`, `/advisory/members/`, `/idcf`, `/*print*`,
`/schedule/archives/`, `/*.PDF$`, `/data.json` — none of which match
`/cpi/tables/seasonal-adjustment/*.xlsx`. NOTE: `/*.PDF$` IS disallowed, so the pre-2021
PDF-only factor tables are deliberately out of scope; we ingest only the 2021+ XLSX.

**Access / bot policy:** BLS returns an "Access Denied" apology page to unidentified
automated agents (server-load protection, not an auth wall or CAPTCHA). BLS's documented
practice is to identify automated requests with a descriptive User-Agent including contact
information; doing so returns the file normally. We send the repo's standard identifying UA
(`inflation-nowcast-research/0.1 ... contact zinuoashley@gmail.com`, per pipelines/_ingest.py).
No login, no CAPTCHA, no robots-disallowed path — consistent with CLAUDE.md rule 5.

**Terms:** BLS public data may be freely used and redistributed with attribution. We store
only the derived projected-factor values (public-domain government statistics), timestamped
by retrieval with a provenance record (url, sha256, bytes) per CLAUDE.md rule 4.
