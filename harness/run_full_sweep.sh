#!/usr/bin/env bash
# M3ToolEval sweep: models x domains x arms, epochs=3.
# Resumable (per-combo markers) + single-instance (flock). Set OPENROUTER_API_KEY.
set -u
cd "$(dirname "$0")"

OUT=out/m3_final
mkdir -p "$OUT/done"
: "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY in your environment}"
INSPECT=${INSPECT:-inspect}

# single instance
exec 9>"$OUT/.lock"
flock -n 9 || { echo "$(date -Is) another instance running; exit"; exit 0; }

echo "$(date -Is) sweep start (pid $$)"

MODELS=(
  "qwen/qwen3-235b-a22b-2507"
  "qwen/qwen3-30b-a3b"
  "qwen/qwen3-coder-30b-a3b-instruct"
  "deepseek/deepseek-chat-v3-0324"
  "qwen/qwen3-14b"
  "qwen/qwen3-32b"
  "qwen/qwen3-8b"
)
DOMAINS=(message_decoder dna_sequencer travel_itinerary_planning trade_calculator)

for MODEL in "${MODELS[@]}"; do
  TAG=$(echo "$MODEL" | sed 's#.*/##')
  for DOM in "${DOMAINS[@]}"; do
    for CM in false true; do
      KEY="${TAG}__${DOM}__${CM}"
      [ -f "$OUT/done/$KEY" ] && continue
      echo "$(date -Is) RUN $KEY"
      ACC=$(timeout 1800 "$INSPECT" eval m3_eval.py@m3 -T domain="$DOM" -T codemode="$CM" \
        --model "openrouter/$MODEL" --epochs 3 --temperature 0 \
        --max-connections 16 --fail-on-error 0.6 --log-dir "./$OUT" 2>>"$OUT/run.log" \
        | grep -E "accuracy" | head -1 | awk '{print $2}')
      if [ -n "$ACC" ]; then
        printf "%s\t%s\t%s\t%s\n" "$TAG" "$DOM" "$CM" "$ACC" >> "$OUT/results.tsv"
        touch "$OUT/done/$KEY"
        echo "$(date -Is) OK  $KEY acc=$ACC"
      else
        echo "$(date -Is) FAIL $KEY (no accuracy; will retry next pass)"
      fi
    done
  done
done

# DONE only if every combo has a marker
EXPECTED=$(( ${#MODELS[@]} * ${#DOMAINS[@]} * 2 ))
HAVE=$(ls "$OUT/done" | wc -l)
echo "$(date -Is) pass complete: $HAVE/$EXPECTED combos done"
if [ "$HAVE" -ge "$EXPECTED" ]; then
  touch "$OUT/DONE"
  echo "$(date -Is) ALL DONE"
fi
