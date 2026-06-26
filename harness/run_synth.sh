#!/usr/bin/env bash
# Synth aggregation sweep: codemode (forced invocation) vs classic across the
# model ladder. Resumable (per-combo markers) + single-instance (flock).
set -u
cd "$(dirname "$0")"
OUT=out/m3_synth
mkdir -p "$OUT/done"
: "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY in your environment}"
INSPECT=${INSPECT:-inspect}

exec 9>"$OUT/.lock"
flock -n 9 || { echo "$(date -Is) another instance running; exit"; exit 0; }
echo "$(date -Is) synth sweep start (pid $$)"

MODELS=(
  "qwen/qwen3-235b-a22b-2507"
  "qwen/qwen3-30b-a3b"
  "qwen/qwen3-coder-30b-a3b-instruct"
  "qwen/qwen3-14b"
  "deepseek/deepseek-chat-v3-0324"
  "qwen/qwen3-8b"
)
# arm label -> -T flags
declare -A ARMS=(
  [classic]="-T codemode=false"
  [codemode]="-T codemode=true -T force=true"
)

for MODEL in "${MODELS[@]}"; do
  TAG=$(echo "$MODEL" | sed 's#.*/##')
  for ARM in classic codemode; do
    KEY="${TAG}__${ARM}"
    [ -f "$OUT/done/$KEY" ] && continue
    echo "$(date -Is) RUN $KEY"
    ACC=$(timeout 1800 "$INSPECT" eval synth_agg.py@synth ${ARMS[$ARM]} \
      --model "openrouter/$MODEL" --epochs 3 --temperature 0 --max-connections 16 \
      --fail-on-error 0.6 --log-dir "./$OUT" 2>>"$OUT/run.log" \
      | grep -E "accuracy" | head -1 | awk '{print $2}')
    if [ -n "$ACC" ]; then
      printf "%s\t%s\t%s\n" "$TAG" "$ARM" "$ACC" >> "$OUT/results.tsv"
      touch "$OUT/done/$KEY"
      echo "$(date -Is) OK $KEY acc=$ACC"
    else
      echo "$(date -Is) FAIL $KEY"
    fi
  done
done

EXP=$(( ${#MODELS[@]} * 2 ))
[ "$(ls "$OUT/done" | wc -l)" -ge "$EXP" ] && { touch "$OUT/DONE"; echo "$(date -Is) ALL DONE"; }
