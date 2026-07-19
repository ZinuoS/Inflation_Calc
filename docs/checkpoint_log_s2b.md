# Session 2B checkpoint log — historical backbone ingestion + reconciliation

## Infrastructure (built)

- `pipelines/_ingest.py` — shared edge-driver helpers (network lives only in pipelines/,
  rule 4): fetch, redact, sha256, raw_dir, staged-CSV writer, provenance writer, FRED
  helper, and `load()` (runs the shared naru artifact + records fetch provenance).
- `pipelines/proxy_loader/v1/` — ONE shared naru artifact loading the uniform proxy
  staged-CSV contract `(source, series_key, frequency, period, value, vintage_status,
  observed_date)` into the governed `proxy_observations` table (key: source, series_key,
  period) with lineage. Golden test passes.
- **Convention adaptation (FLAG for review):** CLAUDE.md says "one folder per source =
  one naru Pipeline Artifact". Because every proxy normalizes at the edge into the same
  uniform schema, the trivial CSV→DB LOAD is shared (proxy_loader), while each source
  keeps its own folder for the distinct parts: license_note.md, spec.yaml (with
  vintage_status), deterministic parse in fetch.py, provenance, and a golden raw sample +
  parse test. This avoids 7× duplication of identical artifacts. **OK to proceed this
  way, or do you want a literal per-source naru artifact each?**

## Decisions (approved at first Group-A checkpoint)
1. Keep the shared proxy_loader artifact (not per-source naru artifacts).
2. Build discovery sources now (apartment_list/indeed/atlanta_fed); defer nadac/usda
   index construction.

## CHECKPOINT A — Group A ingestion  ·  5 built + infra  ·  RESOLVED

Final loaded proxy_observations:

| source | maps to (weight) | rows | range | freq | vintage_status |
|---|---|---|---|---|---|
| zori | Rent + OER (33%) | 138 | 2015-01→2026-06 | monthly | revised_latest_only |
| eia_gasoline | Gasoline (2.90) | 1868 | 1990-08→2026-07 | weekly | unrevised |
| eia_heating_oil | Fuel oil (0.08) | 10074 | 1986-06→2026-07 | daily | unrevised (spot≠retail) |
| atlanta_fed_wage | Services monitor | 353 | 1997-01→2026-06 | monthly | revised_latest_only |
| indeed_wage | Services monitor | 90 | 2019-01→2026-06 | monthly | revised_latest_only |

Atlanta Fed + Indeed resolved via FRED (`FRBATLWGTUMHWGO`) and GitHub
(`hiring-lab/indeed-wage-tracker`, CC BY 4.0) respectively. Both are MONITOR sources
(wage-growth rates, not price proxies) — flagged as such in spec + mapping.

**Deferred, documented (not fought):**
- `apartment_list` (rent backup): licence OK (freely-available research CSV), but the
  download is behind a JS dropdown (no static URL). ZORI is the primary shelter proxy
  already ingested, so this backup is low-urgency — add via browser download later.
- `nadac` (Rx drugs 0.97) + `usda_ams` (food ~2.5): deferred per decision — both need
  an index built from per-NDC / retail-report micro-data (substantial, modelling-adjacent).

### OLD (superseded) — first partial checkpoint

Amendment 1 (vintage_status) recorded in every spec.yaml + mapping.yaml. All writes via
db.connect(). Raw pulls immutable under data/raw/{source}/{date}/. Golden parse tests green.

### Built & loaded (proxy_observations)

| source | maps to (weight) | rows | range | freq | vintage_status | license |
|---|---|---|---|---|---|---|
| zori | Rent SEHA (7.84) + OER SEHC01 (25.23) | 138 | 2015-01 → 2026-06 | monthly | revised_latest_only | Zillow research, attribution required — reviewed |
| eia_gasoline | Gasoline SETB01 (2.90) | 1868 | **1990-08** → 2026-07 | weekly | unrevised | EIA via FRED, public domain — reviewed |
| eia_heating_oil | Fuel oil SEHE01 (0.08) | 10074 | **1986-06** → 2026-07 | daily | unrevised | EIA via FRED, public domain — reviewed |

- Actual depths recorded in mapping.yaml (EIA gasoline 1990 vs planned 1993; heating oil
  1986 vs 1990 — deeper, not padded).
- **eia_heating_oil caveat:** NY-Harbor SPOT (wholesale), not retail — a weak proxy for
  CPI Fuel oil; flagged in license_note + mapping so reconciliation treats it with
  suspicion. Tiny weight (0.08).
- No gaps in the loaded ranges. Provenance rows present (url, retrieved_at, sha256).

### Remaining Group A — honest status (each needs a decision)

| source | maps to | status / blocker |
|---|---|---|
| apartment_list | Rent (backup to ZORI) | Licence: freely available research CSV (2017+), reviewed OK. Direct CSV URL not yet resolved (their download page is JS-gated; static URL 000). Needs URL discovery. |
| atlanta_fed_wage | Services monitor | xlsx reachable (200, 48KB) — needs sheet/column parse. Low priority (monitor source). |
| indeed_wage | Services monitor | Hiring-Lab GitHub repo restructured (old path 404). Needs repo path discovery. Low priority. |
| nadac | Prescription drugs (0.97) | Public-domain (data.medicaid.gov). Requires **index construction** from per-NDC weekly micro-data (matched-NDC basket) — a real modelling-adjacent build, not a single published series. |
| usda_ams | Food strata (~2.5) | Public-domain. Requires **index construction** from weekly retail feature reports — messy, no clean historical national series. Genuinely hard. |

**The single-series proxies (highest clean value: shelter, gasoline) are done.** The
remaining sources split into "URL/repo discovery" (apartment_list, indeed, atlanta_fed —
quick once located) and "index construction from micro-data" (nadac, usda — substantial).

Decision requested: (a) continue Group A now — resolve the 3 discovery sources and build
the 2 index-construction sources; or (b) accept the 3 clean proxies for Group A, defer
nadac/usda index construction, and move toward Groups B/C + the reconciliation harness
where the highest-weight official-vs-proxy pairs already have data (shelter, gasoline).

## Groups B, C, alignment.py, reconciliation — not started (gated on this checkpoint)
