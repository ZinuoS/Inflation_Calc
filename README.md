# inflation-nowcast

Component-level nowcasting of U.S. CPI, PPI, and PCE **surprises** (print minus
consensus, MoM), by replicating official aggregation over published and alternative
data — with a leakage firewall as the first-class design constraint.

## The vintage doctrine, in three sentences

Every backtest target is a **first-release** value read only through a point-in-time
firewall (`src/nowcast/timebase.py`): a value is observable only strictly before its
release datetime, and month-over-month change is computed **within a single vintage** so
a base re-referencing or seasonal restatement can never fabricate a move. A per-series
`vintage_floor` refuses any reference month whose "first release" is actually a
bulk-archived restatement, so restated history can never masquerade as real-time data.
Proxies that publish only a restated history are ingested but flagged **optimistic**, and
short or absent overlaps are reported as `insufficient_overlap` — never replaced by a
small-sample statistic.

## Install

```bash
uv sync                 # Python 3.12; deps pinned in pyproject.toml / uv.lock
uv run pytest           # the firewall + reconciliation tests
```

Historical data is fetched by the pipelines under `pipelines/` and lands in a local,
gitignored SQLite database (`data/db/nowcast.sqlite`); nothing here ships raw data.

## Two-repo boundary

This is the **open-source core**: methodology-replication math, the vintage firewall,
published-proxy ingestion, and the reconciliation harness — built on personal hardware
from public/permissive data only. It ingests and publishes **derived indices and
methodology only**; it never redistributes third-party raw datasets (a source's raw file
is used locally for parsing and is not committed). Any firm-side application layer
(consensus feeds, positioning, live desk use) is separate and out of scope here.

The data layer is [`naru`](https://github.com/ZinuoS/naru-data), a companion library that
turns messy source files into a governed SQLite database deterministically.

## Status

See [`docs/PROGRESS.md`](docs/PROGRESS.md) for an honest, unspun account of what is done,
partial, and not started.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
