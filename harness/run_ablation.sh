#!/usr/bin/env bash
# DeepSeek-V3 codemode adoption ablation: which lever drives run_code invocation.
#   prompt_only : strong system prompt    choice_only : tool_choice=run_code
#   desc_only   : strengthened tool description
set -u
cd "$(dirname "$0")"
OUT=out/m3_ablation
mkdir -p "$OUT/done"
: "${OPENROUTER_API_KEY:?set OPENROUTER_API_KEY in your environment}"
INSPECT=${INSPECT:-inspect}
MODEL=openrouter/deepseek/deepseek-chat-v3-0324

exec 9>"$OUT/.lock"
flock -n 9 || { echo "$(date -Is) another instance running; exit"; exit 0; }
echo "$(date -Is) ablation start (pid $$)"

CONDS=(
  "prompt_only:prompt=strong"
  "choice_only:force_choice=true"
  "desc_only:strong_desc=true"
)
DOMAINS=(message_decoder dna_sequencer travel_itinerary_planning trade_calculator)

for COND in "${CONDS[@]}"; do
  LABEL="${COND%%:*}"
  FLAG="${COND#*:}"
  for DOM in "${DOMAINS[@]}"; do
    KEY="${LABEL}__${DOM}"
    [ -f "$OUT/done/$KEY" ] && continue
    echo "$(date -Is) RUN $KEY (-T $FLAG)"
    ACC=$(timeout 1800 "$INSPECT" eval m3_eval.py@m3 -T domain="$DOM" -T codemode=true -T "$FLAG" \
      --model "$MODEL" --epochs 3 --temperature 0 --max-connections 16 \
      --fail-on-error 0.6 --log-dir "./$OUT" 2>>"$OUT/run.log" \
      | grep -E "accuracy" | head -1 | awk '{print $2}')
    if [ -n "$ACC" ]; then
      printf "%s\t%s\t%s\n" "$LABEL" "$DOM" "$ACC" >> "$OUT/results.tsv"
      touch "$OUT/done/$KEY"
      echo "$(date -Is) OK $KEY acc=$ACC"
    else
      echo "$(date -Is) FAIL $KEY"
    fi
  done
done

EXP=$(( ${#CONDS[@]} * ${#DOMAINS[@]} ))
[ "$(ls "$OUT/done" | wc -l)" -ge "$EXP" ] && { touch "$OUT/DONE"; echo "$(date -Is) ALL DONE"; }
