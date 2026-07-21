# Proxy information-timing audit (Session 3B, Task 2d)

The official side is firewall-protected (`timebase`, `first_release_mom`, vintage_floor). This
closes the **proxy** side: every alternative-data observation gets an `observed_asof` — the
earliest wall-clock date a real-time user could have held that value — from a **documented,
cited publication rule**, and all proxy reads go through a single firewall function.

## STANDING RULE (binding on Session 4)

> **Session-4 feature construction MUST read proxies through
> `nowcast.proxy_timebase.proxy_asof(source, forecast_time, series_key)`, never from
> `proxy_observations` directly.** `proxy_asof` returns only observations with
> `observed_asof <= forecast_time`. This is the exact mirror of the official-side rule
> "backtests may only read rows with observed_asof ≤ forecast_time." A feature that reads a
> proxy value before its `observed_asof` is a look-ahead leak and **invalidates the backtest**
> — treat a failing `test_proxy_timebase` case as a broken build, not a warning.

`observed_asof` is **materialized from the rule**, not a stored column: for most proxies the
true per-observation press date is not recorded across full history — only the publication
*schedule* is documented. The rule is the honest, auditable materialization (verified below).
For `revised_latest_only` sources it is explicitly **estimated** (documented lag + a one-week
conservatism margin) — an additional reason those carry optimism flags.

## Publication rules (spec.yaml `publication` block per source)

| source | vintage | kind | rule → observed_asof | est? | cite |
|---|---|---|---|:--:|---|
| eia_gasoline | unrevised | scheduled | Monday period **+1 day** (pub Mon PM / Tue 10am ET) | no | EIA GDFU notice |
| eia_heating_oil | unrevised | scheduled | daily spot, **next business day** | no | EIA GDFU |
| sp500 (equity_path) | unrevised | scheduled | **same day** (market close final) | no | FRED SP500 |
| manheim (full_month) | unrevised | point_in_time | **first week of M+1** (M+1, +6d) | no | Manheim archive URLs |
| nadac | unrevised | scheduled | **month-end +7d** (CMS weekly, Weds) | no | CMS pharmacy pricing |
| tsa | unrevised | scheduled | **month-end +1d** (daily counts next day) | no | TSA passenger volumes |
| zori | revised_latest_only | estimated | **month-end +25d** (~3rd wk M+1 + 7d margin) | **yes** | Zillow research data |
| atlanta_fed_wage | revised_latest_only | estimated | **month-end +45d** (+7d margin) | **yes** | Atlanta Fed WGT |
| indeed_wage | revised_latest_only | estimated | **month-end +40d** (+7d margin) | **yes** | Indeed hiring-lab |
| apartment_list | revised_latest_only | estimated | **month-end +14d** (+7d margin) | **yes** | Apartment List research |

Rule functions are in `src/nowcast/proxy_timebase.py::observed_asof`; `proxy_asof` applies them
as the firewall. Manheim's separate **mid-month** update (~17th of M, `midmonth_followup`) has
its own `manheim_mid_month` rule for when that series is ingested.

## Verification — publication rules cross-checked against reality (part e)

1. **Manheim full-month = M+1, evidence from the point-in-time archive** (`data/raw/manheim/.../provenance.json`, source URLs are the WordPress upload paths whose `/YYYY/MM/` is the publication month):
   - Jan-2025 index → `…/uploads/sites/2/**2025/02**/Jan-2025-…xlsx` → published **Feb 2025** ✓
   - Feb-2025 index → `…/**2025/03**/Feb-2025-…xlsx` → **Mar 2025** ✓
   - Mar-2025 index → `…/**2025/04**/Mar-2025-…xlsx` → **Apr 2025** ✓
   (All 11 harvested 2025 point-in-time files sit in the M+1 upload directory — the rule is
   evidence-backed for every one, not assumed.) Our `observed_asof("manheim","2025-01-01")`
   = 2025-02-07, inside the verified February publication window.
2. **EIA weekly gasoline** — EIA collects Form EIA-878 at 8:00am each Monday; the Gasoline and
   Diesel Fuel Update publishes Monday afternoons (before 2025-04-07) and Tuesday ~10am ET
   after, "data always represent Monday prices." Our rule (Monday +1 day) is conservative for
   both regimes. Cite: EIA publication-date notice.
3. **TSA / SP500** — checkpoint counts post next day; equity closes are final same day — both
   real-time-observable, matching same-day / +1-day rules.

## What this unblocks / limits

- Session 4 can build proxy features with a clean conscience: `proxy_asof` guarantees no proxy
  value enters a month-M feature before it was publishable.
- The `estimated` observed_asof on revised_latest_only sources is a *floor on honesty*, not a
  recorded fact — those sources remain optimism-flagged and are monitor-only in reconciliation.
- The T-minus arrival timeline built from these rules is in `docs/availability_calendar.md`.
