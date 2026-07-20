# apartment_list — NOT BUILT this session (JS-gated download)

**Barrier.** The Apartment List rent CSV is served through a client-side JavaScript
"Download Report" dropdown; no static URL resolves (research page, CDN guesses, and an
S3 path that only returns a 301 loop). Per CLAUDE.md rule 5 (no fighting blockers for a
proxy) and D1 (public/permissive only), we do not automate a headless-browser download.

**Why low-urgency.** ZORI is the PRIMARY shelter proxy and is already ingested + reconciled;
Apartment List is its BACKUP. The reconciliation already shows the shelter H2 result
(ZORI vs CPI Rent/OER: R²≈0.01, unstable). Apartment List, being another market-rent
index, is expected to replicate that near-zero contemporaneous result.

**To enable.** Manually download `Apartment List Rent Estimates` (national) from
apartmentlist.com/research/category/data-rent-estimates into
`data/raw/apartment_list/{date}/` and run a parse (spec.yaml). The parser is trivial
(same shape as ZORI: pick the United States row, month columns -> monthly series).
The official side (SEHA vintages) is already loaded.
