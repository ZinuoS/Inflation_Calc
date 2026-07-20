# License note — tsa (TSA checkpoint passenger throughput)

Reviewed: 2026-07-19.

**Source.** U.S. Transportation Security Administration — daily checkpoint travel
numbers, `https://www.tsa.gov/travel/passenger-volumes` (HTML table: Date, Numbers).

**Terms.** U.S. Government work, public domain. One fetch per run, identified UA, well
under human-browsing intensity. No auth wall, no CAPTCHA; robots.txt of tsa.gov permits
/travel/. Attribution to TSA retained in provenance.

**Vintage status.** `unrevised` — a day's checkpoint count is published final and not
restated. (The public page shows only ~the trailing ~6 months of daily values; deeper
history is not offered as a clean download and is NOT chased via archives.)

**Role.** MONITOR / demand context for Airline fares (SETG01) — TSA throughput is a
DEMAND signal, not a price. Recorded low-confidence, monitor-only; never a price proxy.
Complete calendar months only; the partial current month is dropped (never interpolated).
