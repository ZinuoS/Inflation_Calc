# License note — cleveland_nowcast (Cleveland Fed inflation nowcast)

Reviewed: 2026-07-24.

**Source.** Federal Reserve Bank of Cleveland, "Inflation Nowcasting,"
`https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting`. Data pulled from the
page's own public webchart feed `.../webcharts/inflationnowcasting/nowcast_month.json`.

**Terms.** U.S. Federal Reserve work — public domain, freely redistributable with attribution.
robots.txt of clevelandfed.org permits `/-/media/`. One fetch per run, identified UA, well under
human-browsing intensity. No auth wall, no CAPTCHA. Attribution to the Cleveland Fed retained in
provenance and in every doc that reports the benchmark.

**What is stored.** Only the numeric nowcast values (percent MoM, SA) and their pre-release
as-of dates — derived facts, not page text. The raw JSON is kept immutable under `data/raw/`
(gitignored) for reproducibility; the committed artifact is the parsed
`data/benchmarks/cleveland_nowcast.csv`.

**Vintage.** `point_in_time`. Each row's value is the daily nowcast immediately BEFORE that
reference month's release vline, so it is strictly what was public before the print — leakage-safe
by construction. Validated: MAE vs SA first-release actual = 0.186pp headline / 0.084pp core over
152 months, matching the Cleveland Fed's published accuracy.

**Role.** Benchmark only. Never a proxy feature, never a backtest target. Held outside
`proxy_observations` to keep it off the feature firewall.
