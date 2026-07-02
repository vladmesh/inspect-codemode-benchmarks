# Synthetic aggregation: classic vs codemode

A small benchmark (`harness/synth_agg.py`): two tools return native structured data —
`get_orders()` and `get_customers()`, each a `list[dict]`. The 20 tasks need filtering,
aggregation, grouping, top-k and joins across the two tools. The classic arm gets the data
as a serialized text blob (~5.7k chars) and must compute by eyeballing it; the codemode arm
gets the native objects and runs the query. `epochs=3`, `temperature=0`.

Run 2026-07-02 on the current head of PR
[#4205](https://github.com/UKGovernmentBEIS/inspect_ai/pull/4205)
(`elenaars:codemode-tool-draft`, commit `0a01c617`).
Data: [synth_aggregation.csv](synth_aggregation.csv). Logs:
[`../logs/synth_aggregation_v2/`](../logs/synth_aggregation_v2/); the previous run
(2026-06-26, pre-review branch) is in [`../logs/synth_aggregation/`](../logs/synth_aggregation/).

| model | classic | codemode | gap |
|---|---:|---:|---:|
| qwen3-coder-30b-a3b | 0.350 | **1.000** | **+65.0pp** |
| deepseek-chat-v3-0324 | 0.483 | **0.983** | **+50.0pp** |
| qwen3-235b-a22b-2507 | 0.733 | **1.000** | **+26.7pp** |
| qwen3-14b | 0.833 | **1.000** | **+16.7pp** |
| qwen3-30b-a3b | 0.967 | 0.950 | −1.7pp |

- In the structured-data + aggregation regime, codemode wins clearly and broadly (+17 to
  +65pp), not only for code-tuned models.
- The gap is largest where the classic baseline is weak — a model that is poor at reading a
  long serialized blob (qwen3-coder, 0.35) is perfect with code (1.0).
- It ties where classic is already near-ceiling (qwen3-30b: 0.97 vs 0.95).
- Three models hit 1.000 with codemode on this run; the pattern from the 2026-06-26 run
  holds and is slightly stronger.

(qwen3-8b classic is 0.650; its codemode cell is empty because this arm forces
`tool_choice=run_code` and the OpenRouter provider for qwen3-8b rejects `tool_choice`
in thinking mode with a 400 error.)
