# Methodology

## The two arms

Both arms share the same dataset, scorer and model; they differ only in the tool layer,
set by a solver step:

- **classic** — the model is given the benchmark's tools directly and calls them with
  Inspect's normal loop (`generate(tool_calls="loop")`). Structured tool results are
  serialized to text, per Inspect's `ToolResult` contract.
- **codemode** — the same tools are wrapped in a single `run_code(tools=...)` tool (the
  default `executor="monty"` runs the code); the model writes Python that calls them as
  async functions in one code block. Structured returns (`list`/`dict`) cross into the
  sandbox as native Python values.

The codemode arm gets a short system message telling it to call the functions from inside
`run_code` and to state its final answer. For models that won't invoke `run_code`, an
optional `tool_choice=run_code` forces it (see `results/deepseek_adoption.md`).

## Models

Via OpenRouter: `qwen3-235b-a22b-2507`, `qwen3-30b-a3b`, `qwen3-coder-30b-a3b-instruct`,
`qwen3-14b`, `qwen3-8b`, `deepseek-chat-v3-0324`.

## Runs and scoring

- `temperature=0`, `epochs=3` (each task run 3× and reduced).
- Two full runs exist: 2026-06-26 on `vladmesh:fix/run-code-structured-tool-returns`
  (before the PR-review changes) and 2026-07-02 on the PR #4205 head
  (`elenaars:codemode-tool-draft`, commit `0a01c617`). Headline tables use the 2026-07-02
  run; the DeepSeek `tool_choice` ablation was only run on 2026-06-26.
- The scorer extracts the final answer (after `Answer:`) from the model's last message and
  compares to the target with type coercion and `ast.literal_eval`, so `615`, `615.0` and
  `"615"` all match.

## Benchmarks

- **M3ToolEval** — ported from [xingyaoww/code-act](https://github.com/xingyaoww/code-act)
  (MIT), the benchmark from the CodeAct paper. Four function domains (message_decoder,
  dna_sequencer, trade_calculator, travel_itinerary), 48 tasks. Tools are built from the
  original definitions; see `harness/m3_eval.py` + `harness/m3src/`.
- **Synthetic aggregation** — `harness/synth_agg.py`: two tools return native `list[dict]`
  (orders, customers); 20 tasks need filtering, aggregation, grouping and joins.
