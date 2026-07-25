# inflation-nowcast — repo conventions

Component-level CPI/PPI/PCE nowcasting: forecasts MoM surprises vs consensus for
core/headline CPI, PPI final demand, and core PCE, via component-level aggregation
replicating official methodology.

Doctrine pointers:
- Research plan: `docs/research_plan.md` (v0.2 companion; authoritative for phases,
  source table, and pre-registered hypotheses H1–H5).
- Session prompts: one self-contained prompt per session; run in order
  (2A before 2B; 3A before 3B; 5 may interleave after 2B).
- ML validation doctrine: the `ash-ml-doctrine` skill is binding for all model
  fitting and evaluation work (Session 4+).
- Data layer: `naru` (local library at `/Users/zinuoshi/naru`, PyPI `naru-data`,
  import/CLI `naru`). Read its README + `docs/spec.md` before designing pipelines.

## Repo layout

```
inflation-nowcast/
├── CLAUDE.md                  # this conventions block + doctrine pointers
├── mapping/
│   └── mapping.yaml           # component map: stratum → sources → weights (Phase 1 output)
├── notebooks/                 # exploration ONLY; numbered nb01_, nb02_ per phase
├── pipelines/                 # one folder per source = one naru Pipeline Artifact
│   ├── alfred_vintages/
│   ├── bls_cpi_weights/
│   ├── manheim/
│   └── ...                    # each: pipeline.py + spec.yaml + license_note.md
├── data/
│   ├── raw/                   # immutable pulls: raw/{source}/{YYYY-MM-DD}/...  never edited
│   └── db/nowcast.sqlite      # single governed DB, written ONLY by naru pipelines
├── src/nowcast/               # importable package: index math, bridge, validation
├── tests/                     # pytest; golden fixtures in tests/fixtures/
└── docs/                      # acceptance reports, per-phase checkpoint logs
```

## Hard rules (repeat in every session)

1. Notebook-first, package-final: explore in notebooks/, but any logic that survives
   a checkpoint moves to src/nowcast/ with tests; notebooks then import it. No business
   logic lives only in a notebook past its phase gate.
2. All data ingestion goes through naru pipelines. Raw pulls land in data/raw/
   (immutable, timestamped); parsed output lands in data/db/nowcast.sqlite via a frozen
   naru Pipeline Artifact. Nothing writes to the DB except naru.
3. naru gap protocol: if naru lacks a capability (HTTP fetch step, xlsx sheet handling,
   X-13 wrapper, vintage/bitemporal keys), do NOT hack around it inside this repo.
   Stop, write the gap as a naru issue stub in docs/naru_gaps.md (desired API, minimal
   example), implement the smallest local shim clearly marked `# SHIM: pending naru#<n>`,
   and continue. This project is naru's torture test — gaps are a deliverable, not a
   failure.
4. Determinism: no LLM calls at runtime, no network calls inside index/bridge/validation
   code. Network only inside pipelines/, and every pipeline run logs (url, retrieval
   timestamp, bytes hash) into a provenance table.
5. Licensing & acquisition: every pipelines/{source}/ folder contains license_note.md
   (ToS/robots.txt review, date checked). A source without a license note does not get a
   pipeline. No auth walls, no CAPTCHA circumvention. Where a source offers no API or bulk
   download, scraping — including screenshot/OCR extraction — is permitted as a last
   resort, provided (a) robots.txt is respected, (b) the license_note records the ToS
   review, and (c) where the ToS restricts redistribution, the extracted data stays local
   (gitignored) and only derived results are published. Prefer the cleanest available
   method; document why a workaround was necessary.
6. Vintage discipline: every observation row carries (reference_period, observed_asof).
   Backtests may only read rows with observed_asof ≤ forecast_time. The release calendar
   table is the firewall; treat violations as test failures.
7. Confirmation gates: at each CHECKPOINT, stop, print the checkpoint summary, and wait
   for my explicit go before proceeding. Never batch through checkpoints.
8. Targets are MoM surprises (unrounded where available). No YoY targets anywhere —
   overlapping-label leakage.
