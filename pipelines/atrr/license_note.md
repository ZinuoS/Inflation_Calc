# License note — atrr (BLS research CPI for all tenant regressed rent, R-CPI-ATR)

Reviewed: 2026-07-26.

**Source.** U.S. Bureau of Labor Statistics, *"Research Consumer Price Index for new tenant rent
(R-CPI-NTR) and research Consumer Price Index for all tenant regressed rent (R-CPI-ATR)"*,
`https://www.bls.gov/cpi/research-series/r-cpi-ntr.htm`. Data files:
`r-cpi-ntr-and-r-cpi-atr.xlsx` (current) plus **dated per-quarter archives**
`r-cpi-ntr-and-r-cpi-atr-{YYYY}q{N}.xlsx` (2023q3 → 2025q3 as of review date).

**Terms.** U.S. Government work — public domain, freely redistributable with attribution. bls.gov
robots.txt permits `/cpi/research-series/` (its `Disallow` list covers `/include`, `/scripts`, `/crs`,
`/_private`, `/iisadmin`, `/srchadm`, `/advisory/members/`, `/idcf`, `/*print*`,
`/schedule/archives/`, `/*.PDF$`, `/data.json` — none of which match this path; the files are `.xlsx`,
not `.PDF`). One fetch per file per run, identifying contact UA, well under human-browsing intensity.
No auth wall, no CAPTCHA. Attribution to BLS retained in provenance and in every doc that reports it.

**Revision behaviour (cited verbatim from the source page).** *"Perpetually revised, with recent
periods being prone to large revisions."* → `vintage_status: revised_latest_only`. This is why the
pipeline archives every snapshot: a restated history cannot be backtested from the latest file alone.

**Publication status (cited verbatim, 2026-07-26).** *"Changes to R-CPI-NTR and R-CPI-ATR publication
paused — Due to a lapse in appropriations resulting in uncollected CPI Housing Survey data for October
2025 and competing priorities, BLS paused publication of the R-CPI-NTR and R-CPI-ATR data in April
2026."* The latest available data is **2025q3**. A recurring pull therefore captures no new vintage
until BLS resumes; the pipeline skips byte-identical payloads rather than accumulating duplicates.

**Vintage archive — corrected finding.** BLS **does** publish dated per-quarter archive files. An
earlier note in this repo stated it does not; that was **wrong** and is corrected in
`docs/checkpoint_log_dataquality.md` (H14 annotation). Verified directly: reference quarter 1999q4
reads **102.2753677** in the 2024q2-vintage file versus **102.388** in the current file — the same
quarter, different values, i.e. the dated files are genuine as-published snapshots.

**Role.** Research/monitor input for the rent–OER carry (pre-registered H14, **NOT ADOPTED**). Never a
target (hard rule 8 also bars its published 4-quarter change columns; quarterly changes are derived
from index levels). Ingesting the archive does **not** re-open H14 — that needs its own
pre-registration.
