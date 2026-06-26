# Harness

Reproducible benchmark code for the two arms (classic vs codemode).

## Files

- `m3_eval.py` — M3ToolEval Inspect adapter. Builds Inspect tools dynamically from the
  vendored M3 tool definitions in `m3src/`, and defines the `@task m3` with params
  `domain`, `codemode`, `prompt` (`base`/`strong`), `force_choice`, `strong_desc`.
- `m3src/` — M3ToolEval task/tool definitions, vendored from
  [xingyaoww/code-act](https://github.com/xingyaoww/code-act) (MIT),
  `scripts/eval/m3tooleval/tasks/` (REPL stubbed out — execution goes through `run_code`).
- `m3_arms.py` — shared `SYSTEM` / `CODEMODE_GUIDANCE` prompts and the tolerant `m3_match`
  scorer (also a hand-port of the message_decoder domain).
- `synth_agg.py` — the synthetic aggregation benchmark (`@task synth`).
- `m3_cross.py` — cross-model aggregator over a directory of `.eval` logs (the summary tables).
- `run_full_sweep.sh` / `run_ablation.sh` / `run_synth.sh` — resumable sweep drivers
  (per-combo markers + `flock`); set `OPENROUTER_API_KEY` and they run a model × arm grid.

## Requirements

`run_code` is draft [inspect_ai#4205](https://github.com/UKGovernmentBEIS/inspect_ai/pull/4205)
plus the structured-return fix ([elenaars/inspect_ai#6](https://github.com/elenaars/inspect_ai/pull/6)),
not yet in a release. Install the branch with both (`code-mode` pulls in pydantic-monty):

```bash
pip install "inspect_ai[code-mode] @ git+https://github.com/vladmesh/inspect_ai.git@fix/run-code-structured-tool-returns"
export OPENROUTER_API_KEY=...
```

## Run a single arm

```bash
# classic
inspect eval m3_eval.py@m3 -T domain=trade_calculator -T codemode=false \
  --model openrouter/qwen/qwen3-8b --epochs 3 --temperature 0
# codemode
inspect eval m3_eval.py@m3 -T domain=trade_calculator -T codemode=true \
  --model openrouter/qwen/qwen3-8b --epochs 3 --temperature 0
# codemode with forced invocation (for under-adopting models)
inspect eval m3_eval.py@m3 -T domain=trade_calculator -T codemode=true -T force_choice=true \
  --model openrouter/deepseek/deepseek-chat-v3-0324 --epochs 3 --temperature 0
```

## Aggregate logs into a table

```bash
python m3_cross.py <log-dir>            # e.g. ../logs/m3tooleval
```
