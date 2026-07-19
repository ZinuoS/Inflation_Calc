# Changelog — proxy_loader

## v1 — 2026-07-19

Shared loader for the uniform proxy staged-CSV contract (Session 2B). Each proxy
source's fetch.py normalizes its raw pull into these 7 columns; this artifact loads
them into the governed proxy_observations table (key: source, series_key, period)
with lineage. Per-source license/parse/provenance/golden live in each source folder.

Convention note: CLAUDE.md's "one folder per source = one naru Pipeline Artifact"
is adapted here — the trivial uniform CSV->DB load is shared, while each source's
distinct deterministic parse, license note, provenance, and golden raw sample remain
per-source. Flagged for review at the Group-A checkpoint.
