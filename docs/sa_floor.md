# Seasonal-adjustment & vintage floors on achievable accuracy

Two irreducible error sources bound how accurate a component nowcast can be, before any
model is fit. Both are measured, not assumed.

## 1. Vintage leakage — why latest-vintage backtests overstate skill

A backtest that reads *revised* (latest-vintage) values instead of *first-release* values
is not measuring real-time skill; it is reading the future. Two exhibits from the
Session-2A firewall work (`tests/test_vintage_mom.py`, checkpoint log s2a):

- **PCE re-referencing: 711 bp.** At the 2023 BEA comprehensive update, naive
  cross-vintage MoM for one reference month is **−6.97%** versus the true within-vintage
  first-release **+0.145%** — 711 bp of pure look-ahead a latest-vintage backtest would
  "predict".
- **CPI February seasonal restatement: 3.5 bp, recurring.** Each February BLS restates the
  SA history with revised seasonal factors; a latest-vintage backtest gets a systematic
  ~3.5 bp free edge that recurs every year in the direction of the revision.

The firewall (`timebase.py`, `first_release_mom`, `vintage_floor`) removes both by
construction. This is why the admission table's numbers are first-release only.

## 2. SA replication floor — our X-13 vs BLS published SA

BLS seasonally adjusts each series with a per-series-tuned X-13ARIMA-SEATS spec
(outliers, regARIMA regressors, seasonal filters chosen per series). We apply a **default**
X-13 (`automdl` + default `x11`, auto transform + outlier detection) via
`src/nowcast/seasonal.py`. The gap between the two is a floor on how accurately we can
reproduce the official SA MoM — and therefore on any nowcast of that stratum's SA MoM.

Method: our full-sample X-13 SA of the NSA series (CUUR0000\*) vs BLS published SA
(CUSR0000\*), MoM MAE in bp over the trailing 8 years (`seasonal.sa_replication_mae`).

| stratum | code | n | SA-replication MAE (bp/MoM) | corr | stratum MoM std |
|---|---|--:|--:|--:|--:|
| Apparel | SAA | 86 | **16.6** | 0.966 | ~0.75% |
| Gasoline | SETB01 | 95 | **72.9** | 0.986 | ~5.5% |
| Used cars | SETA02 | 95 | **83.1** | 0.868 | (high) |
| Airline fares | SETG01 | 86 | **95.4** | 0.959 | (high) |

**Every stratum exceeds the 3 bp target — by 5×–30×.** Verified genuine, not a scaling
bug: our SA tracks BLS closely in level and direction (e.g. gasoline our −9.27% vs BLS
−9.69%; apparel our +0.29% vs BLS +0.33%) with matching volatility and 0.87–0.99
correlation. The residual **scales with each stratum's own MoM volatility**: a small
relative SA-method difference becomes tens of bp absolute on volatile series (gasoline,
airfares, used cars), and only ~17 bp on the calmest tested stratum (apparel).

### Implication per stratum (for achievable nowcast accuracy)

- **Apparel (16.6 bp):** the lowest floor here, but still >5× the target. A tuned X-13
  spec (matching BLS's) would likely bring it toward single digits.
- **Gasoline (72.9 bp):** directly relevant to Task 4. Gasoline's reconciliation R²=0.746
  is bounded by the NSA-proxy vs SA-official mismatch; but our SA introduces a 72.9 bp
  method residual of its own. So SA-adjusting the proxy can recover only the part of that
  gap that is *not* our-vs-BLS SA-method difference — the recoverable headroom is smaller
  than the raw NSA/SA gap suggested.
- **Used cars (83.1 bp) / Airfares (95.4 bp):** the SA floor alone is large enough that a
  contemporaneous SA-MoM nowcast of these strata is heavily floor-limited; their value (if
  any) is more likely as *leading* signals (Manheim used-car lead, §lead_profiles) than as
  precise contemporaneous SA-MoM predictions.

**Open decision (Checkpoint 2 halt):** all four exceed 3 bp with a *default* X-13. The
choice is (a) invest in per-series X-13 spec tuning to match BLS (reduces the floor, real
effort), or (b) accept the volatility-scaled SA floor and carry these strata as
lead/monitor signals rather than precise contemporaneous SA-MoM nowcasts. This is the
research-plan K3 risk ("SA replication error swamps component signal") showing up with a
number.
