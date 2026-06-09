#!/bin/zsh
# One-shot synthetic_field backfill resume — scheduled via launchd to fire ~30 min after
# OpenAlex's daily quota resets (00:00 UTC). Resumes the prefill (skips already-computed
# papers), then re-serves via compute_qal. Self-unloads so it doesn't re-fire.
PROJ="/Users/ulrich/projects/academic-ledger"
LOG="/tmp/synth_backfill_scheduled.log"
PLIST="$HOME/Library/LaunchAgents/com.academicledger.synthbackfill.plist"

cd "$PROJ" || exit 1
{
  echo "=== synthetic backfill resume: $(date) ==="
  source .venv/bin/activate
  set -a; source .env 2>/dev/null; set +a
  export AS_OF_YEAR=2026 H_HALFLIFE=6 K_LAMBDA=20 OPENALEX_SNAPSHOT=openalex-2026-06 MODEL_VERSION=qal-0.1
  echo "-- subfield names (for the composition display) --"
  python pipeline/fetch_subfields.py
  echo "-- synthetic_field batch --"
  python pipeline/synthetic_field.py --targets seed-and-leaders --per-community 150
  echo "-- compute_qal --"
  python pipeline/compute_qal.py
  echo "=== done: $(date) ==="
} >> "$LOG" 2>&1

# disable this one-shot job so it doesn't run again next year
launchctl unload "$PLIST" 2>/dev/null
rm -f "$PLIST" 2>/dev/null
