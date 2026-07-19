# License note — release_calendar (FRED/ALFRED release dates)

Reviewed: 2026-07-19.

**Source.** Federal Reserve Bank of St. Louis — FRED® API, endpoint
`fred/release/dates` for release_ids 10 (CPI), 46 (PPI), 50 (Employment
Situation), 54 (Personal Income & Outlays / PCE).

**Underlying data origin.** Release dates originate from BLS and BEA public
release schedules; FRED redistributes them. The values are U.S. Government works
(public domain). Release *times* are not provided by this endpoint and are imposed
by BLS/BEA published convention (08:30 ET) — see spec.yaml.

**Terms.** FRED API Terms of Use (https://fred.stlouisfed.org/docs/api/terms_of_use.html),
reviewed 2026-07-19. Key points honored:
- Attribution to FRED is retained (this note + provenance rows).
- No implication of FRED endorsement.
- Rate limit: the fetcher issues 4 requests total per run (one per release),
  well under FRED's 120 req/min ceiling; identified via a descriptive User-Agent.
- API key is loaded from the environment (`FRED_API_KEY`), never hardcoded, never
  committed, and REDACTED from every stored URL (provenance + source_url column).

**robots.txt.** N/A — this is a documented public API, accessed per its Terms, not
a crawl. No auth wall, no CAPTCHA.

**Backup.** If FRED were unavailable, BLS (`bls.gov/schedule/archives`) and BEA
(`bea.gov/news/schedule`) publish the same dates directly; not needed while the
FRED API is the chosen source (see docs/checkpoint_log — firewall source decision).
