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
