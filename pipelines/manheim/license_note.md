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

**Vintage status.** `unrevised` — VERIFIED (Session-3A Task 0b). The point-in-time archive
(11 dated files, Jan–Nov 2025, each file's newest row = that month's first release) was
compared value-by-value against the same months in the latest full download: **all 11
months matched EXACTLY (diff 0.0000)**. Manheim's methodology confirms the only historical
"recalculation" was the one-time 1995→1997 rebasing; "revised" in their notes refers to
the full-month superseding the preliminary MID-month, not restatement of published
full-month values. So the full-month MUVVI is not restated post-publication, and the
historical download (1997→2025, 347 months) equals the first-release series — ingested as
`unrevised`, giving H1 a proper long overlap instead of 11 starved months.

**Residual caveat (honest).** The exact-match evidence spans 2025 only (older dated files
404, so no point-in-time comparison is possible pre-2025). No rolling/within-year revision
is observed and the methodology gives no annual-restatement mechanism, but an annual
SA-factor revision of pre-2025 history cannot be positively ruled out from available
point-in-time files. Re-verify at a year boundary when a Dec/Jan dated file is captured.

**Mid-month series** remains a distinct H1 follow-up (separate publication; alignment.py
keeps mid vs full-month distinct).

**Mid-month vs full-month.** This pipeline ingests the FULL-MONTH index (the xlsx).
Manheim's separate MID-MONTH release (~15th) is a distinct publication; alignment.py
already mandates keeping the two as DISTINCT series (H1). Mid-month data acquisition is
a documented follow-up (press-release / mid-month report parsing).
