# cox_atp — parser validated, full-series coverage BLOCKED

The deterministic ATP extractor works (golden test passes: anchor "New-Vehicle Average
Transaction Price" -> $49,758). What's blocked is COVERAGE: the monthly report URL slugs
are inconsistent (some months 404 under `{month}-{year}-atp-report`, existing under other
slugs), so URL enumeration recovers only patchy, non-consecutive months — from which no
clean MoM series can be formed. Per doctrine we do NOT ship a patchy/interpolated series.

To complete: crawl the coxautoinc.com insights index / sitemap to enumerate ATP-report
URLs deterministically (naru#8 archive-crawl-ergonomics gap), then run `extract_atp` per
report. Official side (SETA01 new-vehicle vintages) is already loaded.
