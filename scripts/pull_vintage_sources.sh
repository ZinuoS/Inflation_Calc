#!/bin/bash
# Recurring vintage-capture pulls for revised_latest_only sources.
#
# Each pipeline archives an immutable full-history snapshot under
# data/raw/{source}/vintage_{tag}/ and SKIPS byte-identical payloads, so running
# this more often than the sources publish is free — the archive records changes,
# not calendar ticks. Safe to re-run; never overwrites a captured vintage.
set -uo pipefail                      # NOT -e: one source failing must not skip the rest
cd "$(dirname "$0")/.." || exit 1
REPO="$PWD"
LOG="$REPO/logs/vintage_pulls.log"
PY="$REPO/.venv/bin/python"

log(){ echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >> "$LOG"; }

[ -f .env ] && set -a && . ./.env && set +a   # FRED key for the wage sources

log "=== pull run start (host $(hostname -s)) ==="
run_pipeline() {                      # $1 = source name, $2... = extra fetch kwargs
  local src="$1"; shift
  local kw="${1:-}"
  out=$(PYTHONPATH="$REPO/src:$REPO/pipelines" "$PY" - <<PYEOF 2>&1
import importlib.util, sys
sys.path.insert(0, "$REPO/pipelines")
spec = importlib.util.spec_from_file_location("f", "$REPO/pipelines/$src/fetch.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.fetch($kw)
PYEOF
)
  status=$?
  log "$src: exit=$status"
  echo "$out" | sed "s/^/  [$src] /" >> "$LOG"
}

run_pipeline atrr "backfill=False"    # BLS archive already captured; quarterly, currently paused
run_pipeline zori
run_pipeline atlanta_fed_wage
run_pipeline indeed_wage
log "=== pull run end ==="
