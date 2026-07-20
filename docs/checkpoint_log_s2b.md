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

## Task 2 — alignment.py  ·  DONE
`src/nowcast/alignment.py`: monthly alignment to BLS reference conventions, each cited.
Weekly/daily energy → monthly MEAN of within-month observations (BLS collects prices
throughout the month; mirrors FRED GASREGM-from-GASREGW). Monthly proxies → identity.
Manheim mid- vs full-month recorded as the binding "keep DISTINCT series" convention for
when it lands (Group B). Offline, via db.connect.

## Task 3 — reconcile.py + nb02  ·  CHECKPOINT FINAL

`src/nowcast/reconcile.py` + `notebooks/nb02_reconciliation.ipynb` (executes clean, 2
figures) + `docs/reconciliation_report.md`. Amendment 2 enforced: official MoM via
`timebase.asof_mom_for_ref` (first-release, within-vintage) only; shutdown/series-start
months counted in `skipped`, never imputed; every revised_latest_only proxy stat
optimism-flagged. Results written back to mapping.yaml under `reconciliation:`.

### Reconciliation table (sorted by CPI weight × R²)

| pair | CPI wt | n | skip | beta | R² | quality | optimistic |
|---|--:|--:|--:|--:|--:|---|:--:|
| EIA gasoline vs CPI Energy | 2.90 | 428 | 3 | +0.438 | 0.758 | **stable** | |
| ZORI vs CPI Shelter (SAH1) | 35.62 | 135 | 2 | +0.089 | 0.031 | unstable | ✓ |
| ZORI vs CPI Rent | 7.84 | 135 | 2 | +0.042 | 0.007 | unstable | ✓ |
| EIA heating-oil spot vs CPI Energy | 0.08 | 478 | 3 | +0.153 | 0.266 | unstable | |
| Atlanta Fed wage tracker | — | 353 | 0 | — | — | monitor | ✓ |
| Indeed wage tracker | — | 90 | 0 | — | — | monitor | ✓ |

Optimism-flagged pairs: 4. UNSTABLE: 3 (diagnoses in reconciliation_report.md).

### Feature-admission read (decides Session 4)
- **Admit:** gasoline (stable, R²=0.76) — caveat: reconciled vs Energy AGGREGATE (SETB01
  stratum vintages not yet loaded) and NSA-proxy vs SA-official; tighten in Session 3A.
- **Do NOT admit as contemporaneous next-print feature:** ZORI. R²≈0.01, sign-flipping
  beta — the pre-registered **H2** result (market-rent leads all-tenant CPI rent by ~1yr).
  Its value is as a LEADING indicator, a Session-4 lead/lag question, not next-print rent MoM.
- **Monitors:** Atlanta Fed, Indeed — context only.

### Honest limitations (for your review)
1. Official gasoline stratum (CUSR0000SETB01) vintages not loaded → gasoline reconciled
   vs CPI Energy aggregate (coarse) with an SA/NSA mismatch. A tighter pair needs SETB01
   first-release vintages (small 2A-style add) + SA of the proxy (Session 3A).
2. OER (SEHC01) has no official vintages loaded → ZORI reconciled vs Rent (SEHA) + Shelter
   (SAH1) only. The 25% OER weight is represented by the rent pair as a stand-in.
3. Deferred sources (apartment_list, nadac, usda) not in the table — no data yet.

## Definition of done
Pipelines frozen with provenance + golden tests; 47 tests green; reconciliation_report.md
written; mapping.yaml updated (proxy_quality + vintage_status + reconciliation block);
naru_gaps.md unchanged this task (no new gaps — archive-crawling ergonomics not hit since
Group A sources were APIs/static files, not crawls). checkpoint log appended.

## Session-2B completion — pre-step + Group C

### Pre-step (vintage_floor) — DONE
`series_vintage_floor` view (earliest ref with <=70-day release lag = genuine
first-release, per series). timebase raises `PreVintageFloor` for `_for_ref` below the
floor; `asof_mom` skips; reconcile counts `pre_floor_months`. **FLAG:** the Checkpoint-1
premise that gasoline `n` is "unchanged" was off — the floor DROPS gasoline-vs-SETB01
n 430→184, excluding **246 pre-2011 months** computed off the 2011 bulk vintage
(restated-as-first-release, a real leak now closed by construction). R² held ~0.75
(the leak wasn't inflating it). ZORI pairs unchanged (proxy starts 2015, post-floor).

### TASK 2 — Group C official micro-detail  ·  CHECKPOINT 2

New `official_current` table (source, series_id, item_code, seasonal, period, value),
loaded by a shared `official_loader` naru artifact. `vintage_status: official_current`
— methodology replication (3A/3B) ONLY, never a backtest target (targets stay on ALFRED
vintages). All via db.connect; golden parse tests each; provenance rows present.

| pipeline | source | rows | series | range | coverage |
|---|---|---|---|---|---|
| bls_cpi_series | BLS flat files | 268,386 | 501 (231 SA + 270 NSA codes) | 1913→2026 | **181/181 published strata (100%)** |
| ppi_series | BLS API | 2,396 | 30 | 2006→2026 | 12 SA + 12 NSA final demand + 3/4 PCE-source PPIs |

**Every mapping stratum has its official series present or an explicit absence note:**
- CPI: 181/181 published strata covered (100%). 23 unsampled strata = absence by design
  (no published index; weight 2.08).
- PPI: 30/31. **PCU523920523920 (portfolio management) DISCONTINUED 2022-12** (BLS API
  empty; FRED has 2002-2022). Post-2022 → PCE-bridge S&P500-path approximation. Documented.
- BLS seasonal factors: SA (CUSR) + NSA (CUUR) both present → implied factors derivable;
  explicit factor files not separately ingested (unnecessary while SA+NSA both present).
- PCE bridge: 5 bea_imputed components = absence by design (no official price series).

**Not ingested (needs a key — user action):** BEA PCE underlying detail (Table 2.4.4U).
Requires a BEA API key (like FRED). The bridge's official INPUTS (CPI+PPI feeders) ARE
covered so 3A can proceed; 3B PCE-reconstruction VALIDATION needs BEA detail.

**naru#7 (new gap):** naru's per-row supersede UPDATE has no key index → O(n²) bulk
load; the 268k-row CPI load didn't finish in 2 min. Shim: create a `(series_id, period)`
index on official_current before loading (load then completes in seconds). A DB rebuild
must create this index before the big load.
