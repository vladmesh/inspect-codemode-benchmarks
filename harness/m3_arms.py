"""M3ToolEval message_decoder domain (hand-port) + shared prompts and scorer.

Tools and tasks vendored from xingyaoww/code-act (MIT). Provides SYSTEM /
CODEMODE_GUIDANCE and the tolerant m3_match scorer used by m3_eval.py and synth_agg.py.

    inspect eval m3_arms.py@m3_codemode --model <model>
"""

import ast
from textwrap import dedent

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Scorer,
    Target,
    accuracy,
    scorer,
    stderr,
)
from inspect_ai.solver import (
    Generate,
    Solver,
    TaskState,
    chain,
    generate,
    solver,
    system_message,
)
from inspect_ai.tool import Tool, tool

# --- vendored tool functions (xingyaoww/code-act, MIT) ----------------------


def _convert_hex_to_ascii(hex_string: str) -> str:
    return bytes.fromhex(str(hex_string)).decode("utf-8")


def _reverse_string(s: str) -> str:
    return s[::-1]


def _caesar_decode(message: str, shift: int) -> str:
    shift = int(shift)
    return "".join(
        chr((ord(char) - shift - 65) % 26 + 65)
        if char.isupper()
        else chr((ord(char) - shift - 97) % 26 + 97)
        if char.islower()
        else char
        for char in message
    )


def _string_length(s: str) -> int:
    return len(s)


def _minimum_value(*args: float) -> float:
    return min(args)


def _maximum_value(*args: float) -> float:
    return max(args)


# --- inspect tools (same surface for both arms) -----------------------------


@tool
def convert_hex_to_ascii() -> Tool:
    async def execute(hex_string: str) -> str:
        """Convert a hexadecimal string to ASCII.

        Args:
            hex_string: The hexadecimal string to convert.
        """
        return _convert_hex_to_ascii(hex_string)

    return execute


@tool
def reverse_string() -> Tool:
    async def execute(string: str) -> str:
        """Reverse a string.

        Args:
            string: The string to reverse.
        """
        return _reverse_string(string)

    return execute


@tool
def caesar_decode() -> Tool:
    async def execute(message: str, shift: int) -> str:
        """Decode a string using the Caesar cipher.

        Args:
            message: The string to decode.
            shift: The cipher shift.
        """
        return _caesar_decode(message, shift)

    return execute


@tool
def string_length() -> Tool:
    async def execute(string: str) -> int:
        """Find the length of a string.

        Args:
            string: The string to measure.
        """
        return _string_length(string)

    return execute


@tool
def minimum_value() -> Tool:
    async def execute(values: list[float]) -> float:
        """Find the minimum value from a list of numbers.

        Args:
            values: The list of numbers.
        """
        return _minimum_value(*values)

    return execute


@tool
def maximum_value() -> Tool:
    async def execute(values: list[float]) -> float:
        """Find the maximum value from a list of numbers.

        Args:
            values: The list of numbers.
        """
        return _maximum_value(*values)


    return execute


def _tools() -> list[Tool]:
    return [
        convert_hex_to_ascii(),
        reverse_string(),
        caesar_decode(),
        string_length(),
        minimum_value(),
        maximum_value(),
    ]


# --- tasks (instruction + expected_output, computed via the functions) ------

_TASKS: list[tuple[str, str, object]] = [
    (
        "full_alien_message_decoding",
        "Decode an alien message encoded as follows: first, it's encoded in ASCII; "
        "then, it's reversed; and finally, a Caesar cipher with a shift of 5 is applied. "
        "The message is '7a686b7a686d666d686b'.",
        _caesar_decode(_reverse_string(_convert_hex_to_ascii("7a686b7a686d666d686b")), 5),
    ),
    (
        "shortest_caesar_decoded_message",
        "Given a list of hex-encoded strings, decode each one from hex to ASCII, reverse "
        "it, and then apply a Caesar cipher decode with a shift of 4. Find the length of "
        "the shortest decoded message. The list of hex strings is "
        "['636261', '686766', '6365646362', '6867666865'].",
        _minimum_value(
            *[
                _string_length(_caesar_decode(_reverse_string(_convert_hex_to_ascii(h)), 4))
                for h in ["636261", "686766", "6365646362", "6867666865"]
            ]
        ),
    ),
    (
        "specific_decoded_character",
        "Given a hex-encoded string '576562546563686e6f6c6f6779', decode it to ASCII, "
        "reverse it, apply a Caesar cipher decode with a shift of 7.",
        _caesar_decode(_reverse_string(_convert_hex_to_ascii("576562546563686e6f6c6f6779")), 7),
    ),
    (
        "hex_caesar_combined_decoding",
        "Decode a message that was first converted to hexadecimal, then encoded with a "
        "Caesar cipher with a shift of 2. The hex-encoded, Caesar-shifted message is "
        "'4d4f5252'.",
        _caesar_decode(_convert_hex_to_ascii("4d4f5252"), 2),
    ),
    (
        "multi_step_decoding_challenge",
        "Decode a message that went through three steps: first, a Caesar cipher with a "
        "shift of 3; then reversed; and finally, encoded to hexadecimal. The final "
        "hex-encoded message is '726f77746e6153794d'.",
        _caesar_decode(_reverse_string(_convert_hex_to_ascii("726f77746e6153794d")), 3),
    ),
    (
        "length_based_decoding_puzzle",
        "Given three hex-encoded messages, decode each one using the Caesar cipher with a "
        "shift of 6. Find the message that has a length equal to 5 after decoding. The "
        "hex-encoded messages are ['646566', '6a6b6c6d', '68696a6b6c'].",
        [
            m
            for m in [_caesar_decode(_convert_hex_to_ascii(h), 6) for h in ["646566", "6a6b6c6d", "68696a6b6c"]]
            if _string_length(m) == 5
        ][0],
    ),
    (
        "maximum_value_decoding",
        "Decode a list of hex-encoded messages using a Caesar cipher with a shift of 4, "
        "reverse them, and find the numerical maximum value of these decoded strings. "
        "Assume the decoded strings represent integers. The hex-encoded messages are "
        "['313233', '343536', '373839'].",
        _maximum_value(
            *[int(_reverse_string(_caesar_decode(_convert_hex_to_ascii(h), 4))) for h in ["313233", "343536", "373839"]]
        ),
    ),
]

SYSTEM = dedent(
    """
    You solve a task by using the available tools to compute the answer.
    Use the provided tools; do not guess. When you have the final result, output
    it as 'Answer: <result>' on its own, with only the answer value (e.g. a single
    number or string), and nothing else.
    """
)

CODEMODE_GUIDANCE = dedent(
    """
    Your ONLY tool is `run_code`. You cannot call any other function directly.
    To use the available functions, call `run_code` with a `code` argument
    containing Python that calls them as async functions (use `await`). They
    return native Python values (strings, numbers, lists) that you can compose,
    loop over and aggregate. The value of the last expression is returned to you.
    Then give your final 'Answer: <result>'.
    Never emit a tool call for one of the underlying functions directly.
    """
)


# --- tolerant scorer (mirrors M3ToolEval check_answer) ----------------------


def _coerce(s: object) -> object:
    try:
        return int(s)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        try:
            return float(s)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return s


def _check_answer(answer: str, expected: str) -> bool:
    answer = answer.strip()
    if answer == expected or _coerce(answer) == _coerce(expected):
        return True
    try:
        parsed = ast.literal_eval(answer)
        if str(parsed) == expected or _coerce(str(parsed)) == _coerce(expected):
            return True
    except (ValueError, SyntaxError):
        pass
    return str(answer) == str(expected)


@scorer(metrics=[accuracy(), stderr()])
def m3_match() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        completion = state.output.completion or ""
        if "Answer:" in completion:
            ans = completion.rsplit("Answer:", 1)[1].strip()
        else:
            ans = completion.strip()
        ok = _check_answer(ans, target.text)
        return Score(value=CORRECT if ok else INCORRECT, answer=ans)

    return score


# --- arms -------------------------------------------------------------------


@solver
def _set_tools(codemode: bool) -> Solver:
    from inspect_ai.tool import run_code

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        tools = _tools()
        state.tools = [run_code(tools=tools, execute_code=True)] if codemode else tools
        return state

    return solve


def _dataset() -> list[Sample]:
    return [
        Sample(input=instr, target=str(expected), id=name)
        for name, instr, expected in _TASKS
    ]


def _build(codemode: bool) -> Task:
    steps = [system_message(SYSTEM)]
    if codemode:
        steps.append(system_message(CODEMODE_GUIDANCE))
    steps += [_set_tools(codemode), generate(tool_calls="loop")]
    return Task(dataset=_dataset(), solver=chain(steps), scorer=m3_match())


@task
def m3_classic() -> Task:
    return _build(codemode=False)


@task
def m3_codemode() -> Task:
    return _build(codemode=True)
