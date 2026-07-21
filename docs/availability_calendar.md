# Availability calendar — when inputs arrive per print (Session 3B, Task 2d)

Built from the cited publication rules (`docs/proxy_timing_audit.md`), this is the T-minus
arrival timeline for each print: when each input for **reference month M** becomes observable,
relative to that print's release. It is the skeleton of Session 6's daily tracking mode and the
honest answer to *"how early can the calculator know what it knows."* Times are the materialized
`observed_asof` (proxy side) and `release_calendar` dates (official side). Worked example:
**M = May 2025** (CPI print 2025-06-11, PPI 2025-06-12, PCE 2025-06-27).

## CPI (reference month M) — print ≈ M+1, day 11–13

| input | arrives (rule) | May-2025 date | T-minus to CPI | feeds |
|---|---|---|--:|---|
| Manheim **mid-month** update | ~M-17 | 2025-05-17 | **T-25** | used cars (early read) |
| EIA gasoline — final week of M | ~M-end +1 | 2025-05-27 | **T-15** | gasoline (SETB01) |
| S&P-500 / equity path | same day, continuous | →2025-06-10 | **T-1..0** | bridge (PCE) only |
| TSA throughput (month M) | M-end +1 | 2025-06-01 | **T-10** | airfare demand monitor |
| Manheim **full-month** M | first week M+1 (M+1 +6) | 2025-06-07 | **T-4** | used cars (SETA02) |
| NADAC — final week of M | M-end +7 | 2025-06-07 | **T-4** | Rx drugs (SEMF01) |
| **CPI release (ref M)** | M+1 ~11–13 | **2025-06-11** | **T-0** | — |

**Last useful update before the CPI print:** Manheim full-month & NADAC at **T-4** (equity path
is continuous but feeds only the PCE bridge, not CPI). ZORI for month M does **not** arrive
until ~T+14 (below) — it is a *leading* input for the *next* print, never this one.

## PPI (reference month M) — print ≈ M+1, day 12 (± around CPI)

Same proxy arrivals as CPI (PPI lands ~1 day after CPI: 2025-06-12, T+1 vs CPI). The PPI
final-demand healthcare/air-transport components used by the bridge are published on the PPI
release itself; last useful proxy update before PPI ≈ **T-5** (Manheim/NADAC).

## PCE (reference month M) — print ≈ M+1, day 27; the bridge calls on CPI/PPI day

| event | rule | May-2025 date | note |
|---|---|---|---|
| CPI + PPI both out | — | ~2025-06-12 | all bridge inputs now available |
| **Bridge core-PCE call** | same day as CPI+PPI | **~2025-06-12** | our estimate is knowable **~15 days before** the official PCE print |
| ZORI (month M) | M-end +25 | 2025-06-25 | lands after the bridge call; leading input for next month |
| **PCE release (ref M)** | M+1 ~27 | **2025-06-27** | — |

**Last useful update before the PCE print:** the CPI+PPI prints themselves (T-15 before PCE) —
the bridge adds no new information after CPI/PPI day, so the honest PCE call time is **CPI-day**,
~2 weeks ahead of the official PCE release.

## Reading this calendar

- **Generalize the offsets** (day-of-month, typical): Manheim mid-month M-17; EIA final week
  ~M-end; TSA M-end+1; Manheim full-month M+1-06; NADAC M+1-07; CPI M+1-11..13; PPI ~CPI+1;
  PCE M+1-27. Exact dates vary — always read them from `release_calendar` / `observed_asof`,
  never hard-code (rule 6).
- Every arrival time is a materialized `observed_asof`; Session 4 must gate features on it via
  `proxy_asof` (the standing rule). A feature that uses month-M Manheim before ~M+1-06, or
  month-M ZORI before ~M+1-25, is reading the future.
- `estimated` sources (ZORI, wage trackers) use a +7-day conservatism margin, so their T-minus
  is a *late* bound — they arrive no later than shown, possibly a few days earlier.
