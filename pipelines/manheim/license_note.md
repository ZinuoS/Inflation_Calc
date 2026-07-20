# License note — manheim (Manheim Used Vehicle Value Index)

Reviewed: 2026-07-19.

**Source.** Cox Automotive / Manheim — Used Vehicle Value Index (UVVI), the published
monthly index. Point-in-time DATED xlsx files:
`https://site.manheim.com/wp-content/uploads/sites/2/{pubYYYY}/{pubMM}/{Mon}-{Year}-Manheim-Used-Vehicle-Value-Index.xlsx`
(each month's file, as published that month, is a distinct point-in-time snapshot).

**Terms.** The UVVI index is published by Manheim/Cox Automotive for public reference.
Under research-plan D1 we ingest and publish DERIVED INDICES / methodology ONLY — never
redistribute Manheim's raw file. Attribution to "Manheim Used Vehicle Value Index" is
retained in provenance and any published derivative. We fetch static xlsx files under
/wp-content/uploads/ once each, identified UA, well under human-browsing intensity. No
auth wall, no CAPTCHA.

**Vintage status.** `point_in_time` — each dated monthly xlsx is the index AS PUBLISHED
that month; the newest reference-month row in a given file is that month's FIRST-RELEASE
value (what the market traded). Only ~2025-onward dated files remain hosted (older
publications 404), so point-in-time coverage is intentionally SHORT and honest rather
than long-and-revised (Amendment 1). The full revised history back to 1997 exists in the
latest file but would be `revised_latest_only` (optimism-flagged) — not ingested here.

**Mid-month vs full-month.** This pipeline ingests the FULL-MONTH index (the xlsx).
Manheim's separate MID-MONTH release (~15th) is a distinct publication; alignment.py
already mandates keeping the two as DISTINCT series (H1). Mid-month data acquisition is
a documented follow-up (press-release / mid-month report parsing).
