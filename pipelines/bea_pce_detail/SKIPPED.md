# bea_pce_detail — SKIPPED (pending BEA_API_KEY)

Status as of 2026-07-19: **not built** — blocked on a credential, not on design.

**Dependency.** BEA's NIPA underlying-detail price indexes (Table 2.4.4U) come from the
BEA Data API, which requires a free `BEA_API_KEY` (https://apps.bea.gov/api/signup/).
No key is present in `.env`, so per the Checkpoint-2 review this folder is created with
its spec.yaml and this note instead of a pipeline, and the session continues.

**Why it matters (later).** Session 3B validates the CPI/PPI->PCE bridge by
reconstructing core PCE MoM and comparing to BEA's actual component price indexes. The
bridge's official INPUTS (CPI + PPI feeders) are already ingested (Group C), so 3A can
proceed; 3B's reconstruction VALIDATION needs this table.

**To enable.** Add `BEA_API_KEY=...` to `.env` (gitignored, like FRED). Then this
pipeline follows the standard kit: fetch Table 2.4.4U monthly -> official_current
(source=bea_pce_detail), license_note.md (BEA public domain), golden-fixture parse test.
Nothing else in the repo depends on it yet.
