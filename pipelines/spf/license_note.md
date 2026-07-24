# License note — spf (Survey of Professional Forecasters)

Reviewed: 2026-07-24.

**Source.** Federal Reserve Bank of Philadelphia, Survey of Professional Forecasters, historical
median-level file `medianLevel.xlsx`
(`/surveys-and-data/real-time-data-research/median-forecasts`).

**Terms.** U.S. Federal Reserve work — public domain, freely redistributable with attribution.
robots.txt permits `/-/media/`. One fetch per run, identified UA. No auth wall, no CAPTCHA.

**What is stored.** Only the numeric median forecasts (annualized %), the survey (year, quarter),
horizon, and a conservative point-in-time as-of — derived facts, not document text. Raw xlsx kept
immutable under `data/raw/` (gitignored); committed artifact is parsed `data/benchmarks/spf.csv`.

**Vintage.** `point_in_time`; as-of = mid-2nd-month of the survey quarter (the survey deadline),
so the forecast is dated no earlier than it was actually made.

**Role.** Quarterly trajectory benchmark only. Never per-print, never a proxy feature, never a
target.
