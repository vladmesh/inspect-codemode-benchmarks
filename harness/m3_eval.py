"""M3ToolEval ported to inspect: classic vs codemode.

Builds inspect tools dynamically from the vendored M3ToolEval ToolType objects
(m3src/, from github.com/xingyaoww/code-act, MIT). Domains: message_decoder,
dna_sequencer, trade_calculator, travel_itinerary_planning.

    inspect eval m3_eval.py@m3 -T domain=trade_calculator -T codemode=true --model <model>
"""

import contextlib
import importlib
import inspect as pyinspect
import io
import os
import sys

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import Generate, Solver, TaskState, chain, generate, solver, system_message
from inspect_ai.tool import Tool, ToolDef, ToolFunction, run_code

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from m3_arms import CODEMODE_GUIDANCE, SYSTEM, m3_match  # noqa: E402

# Forceful guidance for models (e.g. deepseek-v3) that ignore CODEMODE_GUIDANCE and
# write Python as prose instead of calling run_code.
STRONG_GUIDANCE = (
    CODEMODE_GUIDANCE
    + "\n\nCRITICAL: You MUST call the `run_code` tool to run any Python. Code that "
    "you write in your reply text is NOT executed and scores zero. Do NOT explain or "
    "show code in prose — emit a `run_code` tool call with the code in its `code` "
    "argument. Only after run_code returns a result do you give 'Answer: <result>'."
)

# Layer A: strengthening the run_code TOOL's own model-facing description (vs the
# system prompt). Appended to the tool description for the strong_desc ablation.
STRONG_DESC = (
    " IMPORTANT: To run anything you MUST call this run_code tool with your Python in "
    "the `code` argument. Python you write in your reply text is NOT executed and "
    "produces no result."
)

DOMAINS = [
    "message_decoder",
    "dna_sequencer",
    "trade_calculator",
    "travel_itinerary_planning",
]

_ANN_NAME = {str: "str", int: "int", float: "float", bool: "bool", list: "list", dict: "dict"}


def _ann_name(ann: object) -> str:
    if ann in _ANN_NAME:
        return _ANN_NAME[ann]
    origin = getattr(ann, "__origin__", None)
    if origin is list:
        return "list"
    if origin is dict:
        return "dict"
    return ""


def _make_inspect_tool(tt: object, stringify: bool) -> Tool:
    """Build an inspect Tool from an M3ToolEval ToolType.

    inspect validates tool calls against the wrapper's real signature, so we
    codegen a wrapper with named parameters (variadic *args become a list param)
    that forwards to the original function.

    stringify mirrors M3ToolEval's action modes: non-code modes return str(res)
    (the classic arm; also keeps results inside inspect's ToolResult contract),
    while code mode returns native values (the codemode arm, projected by the
    run_code bridge).
    """
    fn = tt.function  # type: ignore[attr-defined]
    try:
        params = list(pyinspect.signature(fn).parameters.values())
    except (ValueError, TypeError):
        params = None  # builtins like max/min have no introspectable signature

    sig_parts: list[str] = []
    call_parts: list[str] = []
    if params is None:
        sig_parts.append("values: list = None")
        call_parts.append("*_aslist(values)")
        param_names = ["values"]
    else:
        param_names = []
        for p in params:
            if p.kind == p.VAR_KEYWORD:
                continue
            if p.kind == p.VAR_POSITIONAL:
                sig_parts.append(f"{p.name}: list = None")
                call_parts.append(f"*_aslist({p.name})")
                param_names.append(p.name)
                continue
            # inspect requires a type annotation on every tool parameter; default
            # loosely-typed M3 params to str.
            ann = (_ann_name(p.annotation) if p.annotation is not p.empty else "") or "str"
            decl = f"{p.name}: {ann}"
            if p.default is not p.empty:
                decl += f" = {p.default!r}"
            sig_parts.append(decl)
            call_parts.append(p.name)
            param_names.append(p.name)

    call_expr = f"_orig({', '.join(call_parts)})"
    ret = "str(_r)" if stringify else "_r"
    src = (
        f"async def _wrapper({', '.join(sig_parts)}):\n"
        f"    try:\n"
        f"        _r = {call_expr}\n"
        f"    except Exception as _e:\n"
        f'        return f"Error: {{_e}}"\n'
        f"    return {ret}\n"
    )

    def _aslist(x: object) -> list:
        if x is None:
            return []
        return list(x) if isinstance(x, (list, tuple)) else [x]

    ns: dict[str, object] = {"_orig": fn, "_aslist": _aslist}
    exec(src, ns)  # noqa: S102 - controlled codegen from vendored tool signatures
    wrapper = ns["_wrapper"]

    return ToolDef(
        wrapper,
        name=tt.name,  # type: ignore[attr-defined]
        description=tt.description,  # type: ignore[attr-defined]
        parameters={n: n for n in param_names},
    ).as_tool()


def _load_tasks(domain: str) -> list:
    with contextlib.redirect_stdout(io.StringIO()):
        mod = importlib.import_module(f"m3src.impl.{domain}")
    return list(mod.TASKS)


def _domain_tools(domain: str, stringify: bool) -> list[Tool]:
    tt_dict = _load_tasks(domain)[0].tools  # all tasks in a domain share the tool set
    return [_make_inspect_tool(tt, stringify) for tt in tt_dict.values()]


def _dataset(domain: str) -> list[Sample]:
    return [
        Sample(input=t.instruction, target=str(t.expected_output), id=t.name.split("/")[-1])
        for t in _load_tasks(domain)
    ]


def _codemode_tool(domain: str, strong_desc: bool) -> Tool:
    rc = run_code(tools=_domain_tools(domain, stringify=False), execute_code=True)
    if strong_desc:
        base = ToolDef(rc).description or ""
        rc = ToolDef(rc, description=base + STRONG_DESC).as_tool()
    return rc


@solver
def _set_tools(domain: str, codemode: bool, force_choice: bool, strong_desc: bool) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        if codemode:
            state.tools = [_codemode_tool(domain, strong_desc)]
            if force_choice:
                # make the model actually invoke run_code on the first turn
                # (inspect resets tool_choice to auto after the forced call)
                state.tool_choice = ToolFunction(name="run_code")
        else:
            state.tools = _domain_tools(domain, stringify=True)
        return state

    return solve


@task
def m3(
    domain: str = "travel_itinerary_planning",
    codemode: bool = False,
    prompt: str = "base",  # "base" (CODEMODE_GUIDANCE) | "strong" (STRONG_GUIDANCE)
    force_choice: bool = False,  # set tool_choice=run_code on first turn
    strong_desc: bool = False,  # strengthen the run_code tool's own description (layer A)
) -> Task:
    steps = [system_message(SYSTEM)]
    if codemode:
        steps.append(system_message(STRONG_GUIDANCE if prompt == "strong" else CODEMODE_GUIDANCE))
    steps += [_set_tools(domain, codemode, force_choice, strong_desc), generate(tool_calls="loop")]
    return Task(dataset=_dataset(domain), solver=chain(steps), scorer=m3_match(), name=f"m3_{domain}")
