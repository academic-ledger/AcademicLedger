#!/bin/zsh
# Daily, resumable stage-one OID coverage rollout (QaL_spec.md §11). Fires ~90 min after
# OpenAlex's daily budget resets (00:00 UTC) and after the synthetic backfill, so the two jobs
# don't contend for the same budget. coverage_rollout.py is budget-aware and checkpointed: it
# runs as far as the day's budget allows, then exits 0 cleanly; the next day's fire resumes from
# the coverage_progress checkpoints. compute_qal then composes the newly-covered served records.
PROJ="/Users/ulrich/projects/academic-ledger"
LOG="/tmp/coverage_rollout.log"

cd "$PROJ" || exit 1
{
  echo "=== coverage rollout: $(date) ==="
  source .venv/bin/activate
  set -a; source .env 2>/dev/null; set +a
  export AS_OF_YEAR=2026 H_LONG_HORIZON=10 SAMPLE_N=1000 MODEL_VERSION=qal-0.1 \
         OPENALEX_SNAPSHOT=rollout-2026-06 H_HALFLIFE=6
  python pipeline/coverage_rollout.py --steps 123
  echo "-- compose served records (compute_qal) --"
  python pipeline/compute_qal.py
  echo "=== done: $(date) ==="
} >> "$LOG" 2>&1
