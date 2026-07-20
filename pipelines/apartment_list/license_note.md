# License note — apartment_list (Apartment List Rent Estimates)

Reviewed: 2026-07-19.

**Source.** Apartment List — Rent Estimates (national/state/metro monthly, back to
Jan-2017). Published on apartmentlist.com/research (data-rent-estimates).

**Terms.** Freely available research data for non-commercial market analysis with
attribution to Apartment List. Under research-plan D1 we publish indices/methodology
only, never redistribute the raw file.

**Vintage status.** `revised_latest_only` (Amendment 1): Apartment List uses a
repeat-transaction estimate rebased on ACS; the downloaded history is restated. Optimism
flag applies in reconciliation.

**Access barrier (documented, not fought).** The download is behind a JavaScript
"Download Report" dropdown — no static CSV URL resolves (tried the research page,
files/CDN patterns, and an S3 path that only 301-loops). Per rule 5 we do NOT drive a
headless browser to defeat a JS gate for a proxy. See STATUS.md.
