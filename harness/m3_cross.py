"""Cross-model M3ToolEval aggregation: classic vs codemode by model.

Usage: python m3_cross.py out/m3_final [more dirs...]
Epochs-aware (reads epoch-reduced accuracy/stderr from log.results) and reports
the codemode-minus-classic gap, mean LLM turns, and total tokens per arm.
"""

import glob
import sys
from collections import defaultdict

from inspect_ai.log import read_eval_log

# (model, arm) -> accumulators
acc_w: dict[tuple, float] = defaultdict(float)   # sum(acc * n_tasks)
n_w: dict[tuple, int] = defaultdict(int)          # sum(n_tasks)
tok: dict[tuple, int] = defaultdict(int)
turns_sum: dict[tuple, float] = defaultdict(float)
runs: dict[tuple, int] = defaultdict(int)         # sample-runs (n_tasks*epochs)
by_dom: dict[tuple, dict[str, tuple]] = defaultdict(dict)  # (model,dom)->arm->(acc,se)
seen_models: set = set()

for d in sys.argv[1:] or ["out/m3_final"]:
    for f in glob.glob(f"{d}/*.eval"):
        log = read_eval_log(f)
        if log.status != "success" or not log.samples or not log.results:
            continue
        model = log.eval.model.split("/")[-1]
        seen_models.add(model)
        arm = "codemode" if log.eval.task_args.get("codemode") else "classic"
        dom = log.eval.task_args.get("domain", "?").replace("_planning", "")
        acc = se = None
        for sc in log.results.scores:
            a = sc.metrics.get("accuracy")
            s = sc.metrics.get("stderr")
            if a is not None:
                acc = a.value
                se = s.value if s else 0.0
        if acc is None:
            continue
        ntasks = len({s.id for s in log.samples})
        key = (model, arm)
        acc_w[key] += acc * ntasks
        n_w[key] += ntasks
        turns_sum[key] += sum(sum(1 for m in s.messages if m.role == "assistant") for s in log.samples)
        runs[key] += len(log.samples)
        if log.stats and log.stats.model_usage:
            tok[key] += sum(u.total_tokens for u in log.stats.model_usage.values())
        by_dom[(model, dom)][arm] = (acc, se)

ORDER = [
    "deepseek-chat-v3-0324",
    "qwen3-235b-a22b-2507",
    "qwen3-32b",
    "qwen3-coder-30b-a3b-instruct",
    "qwen3-30b-a3b",
    "qwen3-14b",
    "qwen3-8b",
]
models = [m for m in ORDER if m in seen_models] + sorted(seen_models - set(ORDER))


def agg(model: str, arm: str) -> tuple:
    k = (model, arm)
    if not n_w[k]:
        return None
    a = acc_w[k] / n_w[k]
    t = (turns_sum[k] / runs[k]) if runs[k] else 0
    return a, t, tok[k], n_w[k]


print("M3ToolEval: classic vs codemode (epochs=3, temp 0)\n")
hdr = f"{'model':30s} {'classic':>8s} {'codemode':>9s} {'gap':>7s} {'turns c→cm':>13s} {'ktok c→cm':>16s}"
print(hdr)
print("-" * len(hdr))
for m in models:
    c = agg(m, "classic")
    cm = agg(m, "codemode")
    if not c or not cm:
        miss = "classic" if not c else "codemode"
        print(f"{m:30s}  (incomplete: missing {miss})")
        continue
    ca, ct, ck, cn = c
    ma, mt, mk, mn = cm
    print(
        f"{m:30s} {ca:8.3f} {ma:9.3f} {ma - ca:+7.3f} "
        f"{ct:5.1f}→{mt:<6.1f} {ck / 1000:6.0f}→{mk / 1000:<7.0f}"
    )

print("\nper-domain accuracy (classic / codemode):")
for m in models:
    doms = sorted(d for (mm, d) in by_dom if mm == m)
    if not doms:
        continue
    cells = "  ".join(
        f"{d}:{by_dom[(m, d)].get('classic', ('?',))[0]:.2f}/{by_dom[(m, d)].get('codemode', ('?',))[0]:.2f}"
        if isinstance(by_dom[(m, d)].get("classic", ("?",))[0], float)
        and isinstance(by_dom[(m, d)].get("codemode", ("?",))[0], float)
        else f"{d}:?"
        for d in doms
    )
    print(f"  {m:30s} {cells}")
