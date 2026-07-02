# M3ToolEval: classic vs codemode

Inspect port of M3ToolEval (the CodeAct benchmark), 4 function domains, `epochs=3`,
`temperature=0`. Run 2026-07-02 on the current head of PR
[#4205](https://github.com/UKGovernmentBEIS/inspect_ai/pull/4205)
(`elenaars:codemode-tool-draft`, commit `0a01c617`). Per-model below; per-domain in
[m3tooleval_per_domain.csv](m3tooleval_per_domain.csv). Logs:
[`../logs/m3tooleval_v3/`](../logs/m3tooleval_v3/); the 2026-06-26 run (pre-review
branch) is in [`../logs/m3tooleval/`](../logs/m3tooleval/) and
[`../logs/m3tooleval_v2/`](../logs/m3tooleval_v2/).

| model | classic | codemode | gap |
|---|---:|---:|---:|
| qwen3-30b-a3b | 0.410 | **0.528** | **+11.8pp** |
| qwen3-coder-30b-a3b | 0.549 | **0.625** | **+7.6pp** |
| qwen3-235b-a22b-2507 | 0.736 | **0.778** | **+4.2pp** |
| qwen3-8b | 0.410 | 0.375 | −3.5pp |
| qwen3-14b | 0.639 | 0.583 | −5.6pp |
| deepseek-chat-v3-0324 | 0.549 | 0.408 | −14.0pp |

- Codemode wins on the mid-tier MoE (qwen3-30b **+12pp**), the code-tuned model (coder
  **+8pp**) and, on this run, the strongest model too (qwen3-235b **+4pp**).
- The small thinking models (8b, 14b) are roughly neutral to slightly negative; on the
  2026-06-26 run both were positive, so their sign is within run-to-run variance.
- DeepSeek's loss is interface non-adoption, not codemode quality — this arm does not force
  tool use and DeepSeek invokes `run_code` in only 59% of codemode samples (45% on the
  previous run). Forcing `tool_choice=run_code`
  fixes it: on the synthetic benchmark, where the flag is on, DeepSeek scores 0.983 with
  codemode. See [deepseek_adoption.md](deepseek_adoption.md).
- Compared to the 2026-06-26 run the gaps are narrower overall; per-domain accuracies moved
  by up to ±25pp in both arms between runs, so treat single-model gaps as noisy and the
  cross-model pattern (mid-tier and code-tuned models benefit most) as the signal.
- Codemode tends to spend more tokens (verbose code), so its cost advantage is task-dependent.
