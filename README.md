# Inspect `run_code` (codemode) benchmarks

Benchmarks comparing **codemode** vs **classic** native tool-calling in
[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai), across models.

**Codemode** is the `run_code` tool ([inspect_ai#4205](https://github.com/UKGovernmentBEIS/inspect_ai/pull/4205)):
the tools are wrapped in a single `run_code` tool and the model writes Python that calls
them (one code block can orchestrate many tool calls), instead of one tool call per turn.
**Classic** is Inspect's normal function-calling loop over the same tools. Both arms share
dataset / scorer / model and differ only in the tool layer.

`epochs=3`, `temperature=0`, run via OpenRouter. Headline tables below are from the
2026-07-02 run on the current PR head (`elenaars:codemode-tool-draft`, commit `0a01c617`);
the earlier 2026-06-26 run is kept in [`logs/`](logs/) and git history.

## M3ToolEval — port of the CodeAct benchmark (4 tool domains)

| model | classic | codemode | gap |
|---|---:|---:|---:|
| qwen3-30b-a3b | 0.410 | **0.528** | **+11.8pp** |
| qwen3-coder-30b-a3b | 0.549 | **0.625** | **+7.6pp** |
| qwen3-235b-a22b-2507 | 0.736 | **0.778** | **+4.2pp** |
| qwen3-8b | 0.410 | 0.375 | −3.5pp |
| qwen3-14b | 0.639 | 0.583 | −5.6pp |
| deepseek-chat-v3-0324 | 0.549 | 0.408 | −14.0pp |

Codemode wins on the mid-tier MoE, the code-tuned model and (on this run) the strongest
model; the small thinking models are within noise of even. Per-domain accuracies move by
up to ±25pp between runs in both arms, so the cross-model pattern is the signal, not any
single gap. DeepSeek's minus is **not** a codemode weakness: this arm does not force tool
use and DeepSeek invokes `run_code` in only 59% of samples. Setting
`tool_choice=run_code` fixes it — in the synthetic table below, where the flag is on,
DeepSeek is **+50pp**. See [results/deepseek_adoption.md](results/deepseek_adoption.md).
Full table + per-domain: [results/m3tooleval.md](results/m3tooleval.md).

## Synthetic aggregation — structured tool outputs

Two tools return native `list[dict]` (orders, customers); 20 tasks need filtering,
aggregation, grouping and joins. The classic arm gets the data as a text blob and must
compute by eyeballing it; the codemode arm runs the query.

| model | classic | codemode | gap |
|---|---:|---:|---:|
| qwen3-coder-30b-a3b | 0.350 | **1.000** | **+65.0pp** |
| deepseek-chat-v3-0324 | 0.483 | **0.983** | **+50.0pp** |
| qwen3-235b-a22b-2507 | 0.733 | **1.000** | **+26.7pp** |
| qwen3-14b | 0.833 | **1.000** | **+16.7pp** |
| qwen3-30b-a3b | 0.967 | 0.950 | −1.7pp |

When tool outputs are structured and tasks need aggregation, codemode wins clearly and
broadly; it ties only where the classic baseline is already near-ceiling. (qwen3-8b has no
codemode cell: its OpenRouter provider rejects forced `tool_choice` in thinking mode.)
Full table: [results/synth_aggregation.md](results/synth_aggregation.md).

## When does codemode help

Codemode pays off when tools return structured data and the task needs
computation/aggregation/composition over it, and when the model is good at writing code.
It is neutral when tool outputs are human-readable text the model can just read, or when
the task is a short tool-call chain a model handles fine either way. It also tends to use
more tokens (verbose code). Some models must be steered to invoke `run_code` (see the
adoption note).

## Other benchmarks tried (and why they didn't fit)

- **agentdojo** — tools return YAML text. The classic LLM just reads it; codemode would have
  to parse YAML in code, and `yaml` isn't even importable in the sandbox. Codemode loses.
- **tau2** — JSON tool outputs, but multi-turn customer-service (conversational, not
  data-aggregation). Codemode is roughly a tie and costs more tokens.
- **bfcl** — scored by AST-matching the model's emitted tool calls; codemode emits one
  `run_code` call instead, so the scorer doesn't apply.

The takeaway: codemode needs a benchmark whose tools return **structured** data (not
pre-serialized text) and whose tasks need **computation over it**. Worth trying next: a
ToolQA table/database subset, or τ²-style tasks reframed around structured returns.

## Layout

- [`results/`](results/) — summary tables (Markdown + CSV).
- [`logs/`](logs/) — raw Inspect `.eval` logs (`inspect view --log-dir <dir>` or
  `inspect_ai.log.read_eval_log`). `m3tooleval_v3/` and `synth_aggregation_v2/` are the
  2026-07-02 run on the PR head; the other dirs are the 2026-06-26 run. The DeepSeek
  `tool_choice` ablation ([`logs/deepseek_ablation/`](logs/deepseek_ablation/)) was **not**
  rerun; its numbers are from 2026-06-26.
- [`harness/`](harness/) — benchmark code (ports, arms, scorers, run scripts).
- [METHODOLOGY.md](METHODOLOGY.md) — the two arms, scoring and runs.

## Reproduce

`run_code` is not in a released `inspect_ai` yet — install it straight from draft PR
[#4205](https://github.com/UKGovernmentBEIS/inspect_ai/pull/4205) (the structured-return
fix the earlier run needed from a separate branch is merged into the PR now):

```bash
pip install "inspect_ai[code-mode] @ git+https://github.com/elenaars/inspect_ai.git@codemode-tool-draft" openai
export OPENROUTER_API_KEY=...
cd harness
inspect eval m3_eval.py@m3 -T domain=trade_calculator -T codemode=true \
  --model openrouter/qwen/qwen3-235b-a22b-2507 --epochs 3
```

Tables here were produced with the PR head at commit `0a01c617`.
