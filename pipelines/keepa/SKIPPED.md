# keepa — NOT BUILT (no KEEPA_API_KEY)

Status 2026-07-19: skipped cleanly per C3 — `KEEPA_API_KEY` absent from `.env`.

When a key is present, build per the agreed Task-4 spec:
- **license_note.md FIRST** — verify Keepa redistribution limits; the OSS repo may
  publish DERIVED INDICES ONLY, never raw Keepa price series. No colleague-sourced
  basket files (D1b).
- 150–300 ASIN basket defined in spec.yaml BEFORE fetching, mapped to CPI expenditure
  classes, selection rule documented.
- token-budgeted fetches with backoff; `vintage_status: point_in_time` (verify + cite).
- placeholder index; reconciliation vs CPI core-goods strata.

**Pre-registered hypothesis H6** (state in checkpoint log before any run): expect R²
well BELOW gasoline with a stable small beta. A high R² triggers a leakage/alignment
audit, not celebration.
