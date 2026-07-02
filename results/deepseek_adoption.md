# DeepSeek-V3: codemode adoption

> Numbers below are from the 2026-06-26 run on the pre-review branch
> (`vladmesh:fix/run-code-structured-tool-returns`) and were **not** rerun on the current
> PR head — the ablation costs about as much as the whole M3 sweep. The conclusion still
> holds on the 2026-07-02 rerun: unforced adoption is 59% there, and with forced
> `tool_choice=run_code` (synthetic benchmark) DeepSeek scores 0.983.

DeepSeek-V3 scores far below classic in the codemode arm — not because codemode is worse
for it, but because it frequently **does not invoke the tool**. Across 144 codemode
samples it calls `run_code` in only ~45%; the other ~55% it writes the Python as a prose /
markdown block in its reply instead of calling `run_code`, so nothing executes and those
samples score ~0. When it does invoke `run_code` it scores ≈ its classic level.

An ablation isolates the fix (per-condition accuracy, deepseek codemode, 4 domains):

| condition | avg |
|---|---:|
| baseline | 0.29 |
| stronger system prompt | 0.31 |
| stronger tool description | 0.19 |
| **forced `tool_choice=run_code`** | **0.68** |

**Forcing invocation is the only lever that works** — strengthening the system prompt or
the tool's own description does not. Recipe for an under-adopting model:

```python
from inspect_ai.tool import ToolFunction
state.tool_choice = ToolFunction(name="run_code")  # in a solver, before generate()
```

Inspect resets `tool_choice` to auto after the forced call, so this only forces the first
turn. It is best applied per-model, not as a default. Logs:
[`../logs/deepseek_ablation/`](../logs/deepseek_ablation/).
