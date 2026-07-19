# License note — alfred_vintages (ALFRED / FRED point-in-time vintages)

Reviewed: 2026-07-19.

**Source.** Federal Reserve Bank of St. Louis — ALFRED® (Archival FRED) via the FRED
API `fred/series/observations` with a full realtime span, for the series listed in
spec.yaml (CPI/PPI/PCE targets + major CPI component indices).

**Underlying data origin.** BLS (CPI, PPI) and BEA (PCE) — U.S. Government works,
public domain. FRED/ALFRED redistributes them with vintage (point-in-time) metadata.

**Terms.** FRED API Terms of Use (reviewed 2026-07-19). Honored: attribution to
FRED/ALFRED retained (this note + provenance rows); no endorsement implied; rate
limit respected (one request per series, ~18 total per run, well under 120/min);
identified User-Agent. API key from env `FRED_API_KEY`, never hardcoded/committed,
REDACTED in every stored URL.

**robots.txt.** N/A — documented public API accessed per its Terms. No auth wall, no
CAPTCHA.

**Backup.** BLS/BEA publish current values directly; point-in-time vintages are
ALFRED's distinctive contribution (no equivalent free bulk source), so ALFRED is the
sole viable provider for the vintage discipline this project requires.
