#!/bin/zsh
# Drain the synthetic-field view queue (migration 005) on the FREE polite pool. Scheduled hourly
# via launchd (com.academicledger.synthworker). Computes the highest-cited queued papers first and
# persists them to synthetic_field, so paper pages (read-through) and Explore serve the real
# synthetic field from cache. synth_worker.py defaults to the free pool, so this NEVER spends the
# metered OpenAlex budget even though .env exports the premium key.
PROJ="/Users/ulrich/projects/academic-ledger"
LOG="/tmp/synth_worker.log"

cd "$PROJ" || exit 1
{
  echo "=== synth-view worker: $(date) ==="
  source .venv/bin/activate
  set -a; source .env 2>/dev/null; set +a
  export AS_OF_YEAR=2026 H_HALFLIFE=6 K_LAMBDA=20 OPENALEX_SNAPSHOT=openalex-2026-06
  python pipeline/synth_worker.py --limit 120
  echo "=== done: $(date) ==="
} >> "$LOG" 2>&1
