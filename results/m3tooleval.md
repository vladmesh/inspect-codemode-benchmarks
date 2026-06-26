# M3ToolEval: classic vs codemode

Inspect port of M3ToolEval (the CodeAct benchmark), 4 function domains, `epochs=3`,
`temperature=0`. Per-model below; per-domain in
[m3tooleval_per_domain.csv](m3tooleval_per_domain.csv). Logs:
[`../logs/m3tooleval/`](../logs/m3tooleval/) (classic),
[`../logs/m3tooleval_v2/`](../logs/m3tooleval_v2/) (codemode).

| model | classic | codemode | gap |
|---|---:|---:|---:|
| qwen3-30b-a3b | 0.438 | **0.681** | **+24.3pp** |
| qwen3-coder-30b-a3b | 0.528 | **0.674** | **+14.6pp** |
| qwen3-8b | 0.347 | **0.486** | **+13.9pp** |
| qwen3-14b | 0.611 | **0.653** | **+4.2pp** |
| qwen3-235b-a22b-2507 | 0.774 | 0.742 | −3.2pp |
| deepseek-chat-v3-0324 | 0.729 | 0.493 | −23.6pp |

(qwen3-235b is over 3/4 domains — `trade_calculator` excluded.)

- Codemode helps most models — biggest on the mid-tier (qwen3-30b **+24pp**) and the
  code-tuned / small models (coder **+15pp**, 8b **+14pp**); modest on 14b (**+4pp**).
- Roughly neutral / slight loss on the strongest model (qwen3-235b), which handles both
  interfaces well.
- DeepSeek's loss is interface non-adoption, not codemode quality — this arm does not force
  tool use and DeepSeek often doesn't invoke `run_code`. Forcing `tool_choice=run_code` fixes
  it (it is +30pp on the synthetic benchmark, where the flag is on). See
  [deepseek_adoption.md](deepseek_adoption.md).
- Codemode tends to spend more tokens (verbose code), so its cost advantage is task-dependent.
