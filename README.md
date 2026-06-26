# Inspect `run_code` (codemode) benchmarks

Benchmarks comparing **codemode** vs **classic** native tool-calling in
[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai), across models.

**Codemode** is the `run_code` tool ([inspect_ai#4205](https://github.com/UKGovernmentBEIS/inspect_ai/pull/4205)):
the tools are wrapped in a single `run_code` tool and the model writes Python that calls
them (one code block can orchestrate many tool calls), instead of one tool call per turn.
**Classic** is Inspect's normal function-calling loop over the same tools. Both arms share
dataset / scorer / model and differ only in the tool layer.

`epochs=3`, `temperature=0`, run via OpenRouter.

## M3ToolEval — port of the CodeAct benchmark (4 tool domains)

| model | classic | codemode | gap |
|---|---:|---:|---:|
| qwen3-30b-a3b | 0.387 | **0.774** | **+38.7pp** |
| qwen3-coder-30b-a3b | 0.528 | **0.674** | **+14.6pp** |
| qwen3-8b | 0.347 | **0.486** | **+13.9pp** |
| qwen3-14b | 0.559 | **0.677** | **+11.8pp** |
| qwen3-235b-a22b-2507 | 0.774 | 0.742 | −3.2pp |
| deepseek-chat-v3-0324 | 0.729 | 0.493 | −23.6pp |

Codemode helps most models — biggest on the mid-tier, small and code-tuned ones — and is
roughly neutral on the strongest. DeepSeek's minus here is **not** a codemode weakness and
is fixable: this M3 codemode arm does not force tool use, and DeepSeek often does not invoke
`run_code` at all. Setting `tool_choice=run_code` fixes it — in the synthetic table below,
where the flag is on, DeepSeek is **+30pp**. See
[results/deepseek_adoption.md](results/deepseek_adoption.md). Full table + per-domain:
[results/m3tooleval.md](results/m3tooleval.md).

## Synthetic aggregation — structured tool outputs

Two tools return native `list[dict]` (orders, customers); 20 tasks need filtering,
aggregation, grouping and joins. The classic arm gets the data as a text blob and must
compute by eyeballing it; the codemode arm runs the query.

| model | classic | codemode | gap |
|---|---:|---:|---:|
| qwen3-coder-30b-a3b | 0.350 | **1.000** | **+65.0pp** |
| deepseek-chat-v3-0324 | 0.700 | **1.000** | **+30.0pp** |
| qwen3-235b-a22b-2507 | 0.767 | **0.950** | **+18.3pp** |
| qwen3-14b | 0.850 | **0.967** | **+11.7pp** |
| qwen3-30b-a3b | 0.950 | 0.950 | +0.0pp |

When tool outputs are structured and tasks need aggregation, codemode wins clearly and
broadly; it ties only where the classic baseline is already near-ceiling. Full table:
[results/synth_aggregation.md](results/synth_aggregation.md).

## When does codemode help

Codemode pays off when tools return structured data and the task needs
computation/aggregation/composition over it, and when the model is good at writing code.
It is neutral when tool outputs are human-readable text the model can just read, or when a
strong model handles both interfaces equally well. It also tends to use more tokens
(verbose code). Some models must be steered to invoke `run_code` (see the adoption note).

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
  `inspect_ai.log.read_eval_log`).
- [`harness/`](harness/) — benchmark code (ports, arms, scorers, run scripts).
- [METHODOLOGY.md](METHODOLOGY.md) — the two arms, scoring and runs.

## Reproduce

```bash
pip install "inspect_ai[code-mode]" inspect_evals
export OPENROUTER_API_KEY=...
cd harness
inspect eval m3_eval.py@m3 -T domain=travel_itinerary_planning -T codemode=true \
  --model openrouter/qwen/qwen3-235b-a22b-2507 --epochs 3
```
