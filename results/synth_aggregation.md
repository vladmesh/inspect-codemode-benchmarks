# Synthetic aggregation: classic vs codemode

A small benchmark (`harness/synth_agg.py`): two tools return native structured data —
`get_orders()` and `get_customers()`, each a `list[dict]`. The 20 tasks need filtering,
aggregation, grouping, top-k and joins across the two tools. The classic arm gets the data
as a serialized text blob (~5.7k chars) and must compute by eyeballing it; the codemode arm
gets the native objects and runs the query. `epochs=3`, `temperature=0`.
Data: [synth_aggregation.csv](synth_aggregation.csv). Logs:
[`../logs/synth_aggregation/`](../logs/synth_aggregation/).

| model | classic | codemode | gap |
|---|---:|---:|---:|
| qwen3-coder-30b-a3b | 0.350 | **1.000** | **+65.0pp** |
| deepseek-chat-v3-0324 | 0.700 | **1.000** | **+30.0pp** |
| qwen3-235b-a22b-2507 | 0.767 | **0.950** | **+18.3pp** |
| qwen3-14b | 0.850 | **0.967** | **+11.7pp** |
| qwen3-30b-a3b | 0.950 | 0.950 | +0.0pp |

- In the structured-data + aggregation regime, codemode wins clearly and broadly (+12 to
  +65pp), not only for code-tuned models.
- The gap is largest where the classic baseline is weak — a model that is poor at reading a
  long serialized blob (qwen3-coder, 0.35) is perfect with code (1.0).
- It ties where classic is already near-ceiling (qwen3-30b: both 0.95).

(qwen3-8b is omitted: its codemode runs errored out repeatedly on this benchmark.)
