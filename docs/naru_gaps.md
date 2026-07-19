# naru gaps register

Per CLAUDE.md rule 3: when naru lacks a capability this project needs, we do NOT
hack around it silently. We log the gap here (desired API + minimal example),
implement the smallest local shim marked `# SHIM: pending naru#<n>`, and continue.
This project is naru's torture test — gaps are a deliverable.

naru version under test: 0.1.0 (editable, `/Users/zinuoshi/naru`).
Each gap below is written so it can be pasted into `naru`'s issue tracker as-is.

---

## naru#1 — Non-Excel source readers (CSV / TSV / JSON)  ·  severity: BLOCKING  ·  CSV/TSV RESOLVED

> **Resolved for CSV/TSV** in naru branch `feat/csv-tsv-source-reader` (commit 35a2612,
> local, unpushed): `manifest.source_format: xlsx|csv|tsv` + `source_options`, via
> `naru.sources.source_workbook_from_bytes` (delimited bytes → in-memory single-sheet
> Workbook; cells are strings, empty→None; fingerprint/lineage/golden all reused). 9
> new tests; naru suite 464 green. **JSON is still unresolved** → ALFRED JSON is fetched
> then normalized to CSV by the edge driver before `naru run` (shim below).

**Observed.** `runtime.run()` reads the input exclusively as an Excel workbook:
`load_workbook(io.BytesIO(raw_bytes))` (src/naru/runtime.py:119,128), and the
fingerprint engine operates on an openpyxl `Workbook`. There is no code path for
CSV, TSV, or JSON. `naru profile` is likewise documented "…of an Excel file"
(cli.py:93).

**Why it blocks this project.** Almost every Phase-2 source is non-Excel:
ALFRED vintages (CSV or JSON API), BLS flat files (TSV: cu.item, cu.series),
EIA (CSV/JSON), release calendars (HTML). Under CLAUDE.md rule 2 the governed DB
write must go through a frozen naru artifact, but naru cannot currently ingest any
of these formats directly.

**Desired API.** A source-reader abstraction selected by the artifact, e.g. in
`manifest.yaml`:

```yaml
name: alfred_vintages
version: v1
source_format: csv        # xlsx (default) | csv | tsv | json
source_options:           # reader-specific, validated per format
  header_row: 1
  delimiter: ","
target_table: obs_vintages
key: [series_id, reference_period, observed_asof_vintage]
```

`runtime.run()` dispatches on `source_format` to produce the same `_src_row`-tagged
raw grid it already builds from a worksheet; everything downstream (fingerprint,
transform, validations, lineage) is format-agnostic once the grid exists. A CSV
"sheet" fingerprint = the header row's ordered column names + types (naru already
models exactly this for Excel headers).

**Minimal example.** `naru run pipelines/x/v1 data.csv` should behave like the
Excel path: fingerprint the header, hash raw bytes, transform via ops, validate,
load with lineage.

**Local shim (this repo).** `# SHIM: pending naru#1` — a normalizer converts the
fetched raw CSV/TSV/JSON into a single-sheet canonical `.xlsx` in a staging dir,
then `naru run artifact/ staged.xlsx` performs the real governed load. The
immutable raw bytes in `data/raw/` remain the fetched original (not the xlsx);
the xlsx is a disposable transport, re-derivable and never the source of truth.

---

## naru#2 — Fetch provenance columns (url, retrieved_at) in the raw registry  ·  severity: HIGH

**Observed.** `raw_files` stores only `(sha256, original_name, ingested_run_id)`
(store.py:46-50). naru is correctly network-free at runtime, so it has no concept
of *where* bytes came from or *when* they were retrieved.

**Why it matters.** CLAUDE.md rule 4 requires every pipeline run to log
`(url, retrieval timestamp, bytes hash)` into a provenance table. naru captures the
hash but neither the url nor the retrieval time.

**Desired API.** Optional provenance fields accepted by the runner and persisted
on `raw_files`:

```
raw_files(sha256, original_name, ingested_run_id,
          source_url TEXT NULL, retrieved_at TEXT NULL, retrieval_meta TEXT NULL)
```

passed via `naru run … --source-url … --retrieved-at …` or a sidecar
`<input>.provenance.json` that the runner reads (never the network — the caller
supplies these; naru only records them, exactly as it already does for `as_of`).

**Local shim.** `# SHIM: pending naru#2` — the edge fetcher writes a
`provenance.json` next to each raw pull `(url, retrieved_at_utc, sha256,
http_status, bytes)`, and a repo-side `meta_fetch_provenance` table in
`nowcast.sqlite` is populated by the fetcher keyed on sha256, joinable to naru's
`raw_files`/`meta_lineage` by hash.

---

## naru#3 — First-class bitemporal / vintage key + as-of-date view  ·  severity: MEDIUM

**Observed.** naru already has point-in-time storage: `_run_id` /
`_superseded_by_run_id` and `rows_as_of(conn, table, run_id)` (store.py:347). But
"as of" is keyed by **run_id**, not by a *data-carried* observation date. For
vintage discipline we need "the value observable as of an arbitrary wall-clock
`forecast_time`", where the vintage date lives in the row.

**Why it matters.** Rule 6: every observation carries `(reference_period,
observed_asof)`; backtests read only rows with `observed_asof ≤ forecast_time`.
This is expressible today by putting `observed_asof_vintage` **in the natural key**
(so a new vintage never supersedes an older one — both are retained as distinct
active rows) and doing the as-of filter in downstream SQL. naru gives us the
retention and lineage for free; it does not give us the as-of-date view.

**Desired API (nice-to-have).** A declared temporal key in `manifest.yaml`
(`valid_from: observed_asof_vintage`) and a helper
`store.rows_as_of_date(table, ref_key, asof_date)` returning the latest row per
reference key with `observed_asof_vintage ≤ asof_date`.

**Local handling (NOT a shim — sanctioned downstream logic).** This is
`src/nowcast/timebase.py`'s job per the session plan; naru correctly stays a loader.
Logged here only so the "naru could own this" design note isn't lost. No shim tag.

---

## naru#4 — Multi-sheet workbook handling  ·  severity: LOW (not needed in Session 2A)

**Observed.** `manifest.yaml` names exactly one `sheet`; one artifact = one sheet.
The BLS relative-importance workbook has 7 sheets (Table 1–7).

**Desired API.** Either a per-sheet artifact convention (documented) or a
`sheets: [...]` fan-out in the manifest producing one target table per sheet.

**Local handling.** For Session 1 the weights file was read outside naru (hand
generator). When `bls_cpi_weights` becomes a real pipeline (later session), one
artifact per needed sheet is the interim convention. No shim needed now.

---

## naru#5 — Editable install shadowed by force-included examples  ·  severity: MEDIUM (workaround in place)

**Observed.** naru's wheel config force-includes example dirs into the package:
`[tool.hatch.build.targets.wheel.force-include] "pipelines" = "naru/_examples/pipelines"`
(+ examples, recipes). Under an **editable** install, uv unpacks that force-included
data to a physical `site-packages/naru/_examples/`, creating a `site-packages/naru/`
directory that has NO real modules. That physical dir shadows the editable src path
(`_editable_impl_naru_data.pth` → `/Users/zinuoshi/naru/src`, which is appended to
sys.path *after* site-packages), so `import naru` resolves to the empty shadow and
every `import naru.<submodule>` fails (`naru.__file__ is None`). It silently
reappears on every `uv sync`/`uv run` auto-sync.

**Impact here.** Broke the entire nowcast→naru toolchain mid-session (naru.cli,
naru.artifact unimportable; `naru` CLI dead).

**Desired fix (in naru).** Don't force-include example data *inside* the importable
package for editable installs — relocate to a top-level `naru_examples/` distributed
package, or ship examples as separate `[project.optional-dependencies]`/sdist-only
data, or use `tool.hatch.build.targets.wheel.shared-data`. Then `import naru` under
editable installs resolves to src.

**Workaround (this repo).** nowcast installs naru **non-editable**
(`[tool.uv.sources] editable = false`): a full wheel unpack carries the real modules
*and* `_examples`, so there is no shadow. Trade-off: naru changes require
`uv sync --reinstall-package naru-data` to take effect (documented in pyproject).

## naru#6 — Connection lifecycle: no WAL, no busy_timeout, no session context manager  ·  severity: LOW-MEDIUM (workaround in place)

**Symptom (Session 2A).** Repeated "database is locked" errors and multi-minute
hangs when running DB scripts, sometimes leaving a python process holding the file
lock until killed (`lsof -t data/db/nowcast.sqlite`).

**Diagnosis (per rule 3 — root cause, not just the workaround).**
- naru's `runtime.run()` *does* close its connection on every path (`conn.close()`),
  so leaked connections are NOT primarily naru's fault. The hangs came from a
  combination:
  1. **No busy_timeout.** naru opens `sqlite3.connect(db_path)` with SQLite's default
     `busy_timeout = 0`: any lock contention raises "database is locked" *immediately*
     instead of waiting.
  2. **Rollback-journal mode (not WAL).** Under the default journal mode a reader and a
     writer block each other; a single long-running query (our correlated-subquery
     view before it was indexed) or a stuck process holds a lock the whole time.
  3. Our own early inline scripts opened connections without a context manager; when a
     slow `uv run` auto-backgrounded and was killed mid-statement, the OS held the lock
     until process death.
- So: not a naru bug per se, but naru is **fragile under concurrency** and a more
  robust default would have prevented the contention from ever surfacing as a hard
  error/hang.

**Desired API (naru).** A connection/session helper used by the runtime and query
paths that (a) enables `PRAGMA journal_mode=WAL` by default (readers never block the
writer), (b) sets a configurable `PRAGMA busy_timeout` (wait, don't error), and (c) is
a context manager so the connection is always closed. e.g.
`with naru.store.session(db_path) as conn: ...`.

**Local shim (this repo).** `# SHIM: pending naru#6` — `src/nowcast/db.connect()`:
a context manager that sets WAL + a 30s busy_timeout and guarantees close. All
repo-side DB access (timebase, views, provenance) goes through it. WAL is now enabled
persistently on nowcast.sqlite.

## Status log

| date | gap | state |
|---|---|---|
| 2026-07-19 | naru#1 | CSV/TSV RESOLVED in naru (branch feat/csv-tsv-source-reader, 35a2612); JSON still shimmed to CSV at the edge |
| 2026-07-19 | naru#2 | logged; sidecar shim planned |
| 2026-07-19 | naru#3 | logged; handled downstream in timebase.py by design |
| 2026-07-19 | naru#4 | logged; deferred, not needed in 2A |
| 2026-07-19 | naru#5 | workaround: nowcast installs naru non-editable (pinned git rev 35a2612); proper fix is a naru packaging change |
| 2026-07-19 | naru#6 | shim: src/nowcast/db.connect (WAL + busy_timeout + context manager); proper fix is WAL/timeout/session defaults in naru |
