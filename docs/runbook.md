# Runbook

Operational procedures. Every step is a command you can run; nothing auto-sends anywhere.

## Print cycle — pre-print call, realized, postmortem

Per print (CPI and PCE each). All times are relative to that print's release date `T` from
`release_calendar`. Nothing is distributed automatically — pages are written to `docs/prints/`.

| when | action | command |
|---|---|---|
| **T-3** | freeze + generate the pre-print one-pager; appends the call to the pristine ledger (write-once) | `python -c "import datetime as dt;from nowcast import report;report.generate('cpi','YYYY-MM-01',dt.date.today())"` |
| **T+0** | the print lands — realized first-release becomes available (CPI same day; PCE same day) | — |
| **T+2** | run the postmortem: populates realized + deviation, attributes vs published components, appends the postmortem section to the page and fills the ledger row | `python -c "from nowcast import report;report.postmortem('cpi','YYYY-MM-01')"` |

Notes:
- The **T-4 freeze** is enforced in code: an as-of later than T-4 is clamped, because nothing
  useful arrives after it (validated: |T-0 call − T-4 call| = 0.0000 bp).
- A call may be generated **earlier** than T-3 (it will be marked `NOT FROZEN` and carries the
  wider band for that lead) — but it is written to the ledger once and never rewritten.
- **PCE attribution waits for BEA 2.4.4U**: if the postmortem runs before BEA publishes that
  month's component prices, the page says so and attribution populates on the next BEA release.
- To rehearse the loop without touching the pristine ledger:
  `report.postmortem('cpi','YYYY-MM-01', dry_run=True)` → writes a `*_DRYRUN.md` page only.

## Scheduled adjudications — resolved dates (staged 2026-07-25, dates from `release_calendar`)

Each step is executed on its date, not re-decided. **A step never runs early: if the print has not
released, there is no first-release value — the ledger row stays a standing prediction, unpopulated.
Never fabricate a realized value under a T+0 label.** (This staging exists because a session opened
at T-5 and correctly could not adjudicate.)

### Daily (until each print lands) — regenerate the standing status report
```
python -c "from nowcast import pce_status; pce_status.update()"
```
Appends one dated row to `docs/pce_status_log.csv` (idempotent per date) and rewrites
`docs/pce_status_report.md`. It reports `realized = pending` until the first-release value is actually
in the DB — **it never adjudicates and never populates the ledger**; that stays with
`report.postmortem` on the release date.

### Entry #2 — PCE core, ref 2026-06 (call +7.6 bp ±8.0, frozen as_of 2026-07-14)
| date | when | action |
|---|---|---|
| **2026-07-30 (Thu)** | **T+0** | Print lands. Ingest first-release PCEPILFE MoM via the standard pipeline; cross-check the vintage row against `release_calendar`. Populate `realized_bp` on ledger row #2 (`ledger.populate_realized`; hash invariant — `test_ledger` must stay green). Curate the June-PCE press consensus FIRST if a dated preview/recap exists (own as-of, standard citation discipline); else it stays a gap. Deviation vs call, and vs consensus if curated. |
| 2026-07-30 | T+0 | `report.postmortem('pce','2026-06-01')` — verdict line uses the pre-written frame verbatim; **BEA 2.4.4U component attribution = PENDING** (populates on BEA's underlying-detail release, not approximated). |
| — | forward | Append this print to the PR-1/PR-2 forward tracking in `benchmark_evaluation_1.md` (divergence? boundary? verdict); update n and running rates. No threshold or claim edits. |

### Entry #1 — CPI, ref 2026-07 (T-21 call −5.1 bp, NOT FROZEN, as_of 2026-07-22, ledger row #1)
| date | when | action |
|---|---|---|
| **2026-08-09 (Sun)** | **T-3 freeze** | `report.generate('cpi','2026-07-01', dt.date(2026,8,9))`. Intent: the frozen call is a **NEW** ledger row with its own hash; the T-21 page/row #1 stays, marked superseded-by-freeze, **never edited**. ⚠ **PRE-CONDITION:** `ledger.append_call` currently dedupes on `(instrument, ref_month)`, so it will **skip** a second cpi-2026-07 row. Before Aug 9, extend the ledger key to include the freeze/as_of dimension (with a test), or record an explicit supersede — resolve *in the Aug 9 session*, not retroactively. |
| **~2026-08-10/11** | T-2/T-1 | Curate the CPI July press-consensus preview when published (own as-of, standard discipline); if not found, gap. Populate `consensus_bp`/`consensus_asof` on the frozen CPI row. |
| **2026-08-12 (Wed)** | **T+0** | CPI print lands. Same protocol as the PCE T+0 above: ingest first-release NSA MoM, populate `realized_bp`, deviation vs call and vs consensus. |
| **2026-08-14 (Fri)** | **T+2** | `report.postmortem('cpi','2026-07-01')` — full postmortem, component attribution from CPI-side data. |

**Verdict frame (verbatim, both prints):** hit — or *"missed by X bp, inside/outside the published
band; the postmortem ran on schedule; attribution to follow when BEA 2.4.4U components publish; the
row stands unedited."*
