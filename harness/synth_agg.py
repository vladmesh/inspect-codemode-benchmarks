"""Synthetic aggregation benchmark: classic vs codemode.

Two tools return list[dict]; 20 tasks need filtering, aggregation, grouping and joins.
classic gets str(data); codemode gets native objects (force=True forces run_code).

    inspect eval synth_agg.py@synth -T codemode=true -T force=true --model <model>
"""

import os
import sys

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import Generate, Solver, TaskState, chain, generate, solver, system_message
from inspect_ai.tool import Tool, ToolDef, ToolFunction, run_code

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from m3_eval import CODEMODE_GUIDANCE, STRONG_GUIDANCE  # noqa: E402
from m3_arms import SYSTEM, m3_match  # noqa: E402

# --- deterministic dataset --------------------------------------------------
REGIONS = ["North", "South", "East", "West"]
PRODUCTS = ["widget", "gadget", "gizmo", "sprocket", "cog"]
TIERS = ["bronze", "silver", "gold"]
STATUSES = ["shipped", "pending", "cancelled"]

CUSTOMERS = [
    {"id": f"c{i}", "name": f"Customer{i}", "tier": TIERS[i % 3], "region": REGIONS[i % 4]}
    for i in range(12)
]
ORDERS = [
    {
        "id": i,
        "customer_id": f"c{i % 12}",
        "product": PRODUCTS[i % 5],
        "amount": (i * 37) % 500 + 10,
        "qty": (i % 5) + 1,
        "status": STATUSES[i % 3],
        "region": REGIONS[(i * 3) % 4],
    }
    for i in range(48)
]
_CUST = {c["id"]: c for c in CUSTOMERS}


# --- tasks: (id, instruction, expected_output computed over the data) -------
def _by_region_totals() -> dict:
    out: dict[str, int] = {}
    for o in ORDERS:
        out[o["region"]] = out.get(o["region"], 0) + o["amount"]
    return out


def _orders_per_product() -> dict:
    out: dict[str, int] = {}
    for o in ORDERS:
        out[o["product"]] = out.get(o["product"], 0) + 1
    return out


def _cust_totals() -> dict:
    out: dict[str, int] = {}
    for o in ORDERS:
        out[o["customer_id"]] = out.get(o["customer_id"], 0) + o["amount"]
    return out


_TASKS = [
    ("shipped_total", "What is the total `amount` across all orders with status 'shipped'?",
     sum(o["amount"] for o in ORDERS if o["status"] == "shipped")),
    ("count_north", "How many orders have region 'North'?",
     sum(1 for o in ORDERS if o["region"] == "North")),
    ("distinct_products", "How many distinct `product` values appear across the orders?",
     len({o["product"] for o in ORDERS})),
    ("max_amount", "What is the highest order `amount`?",
     max(o["amount"] for o in ORDERS)),
    ("count_over_200", "How many orders have an `amount` strictly greater than 200?",
     sum(1 for o in ORDERS if o["amount"] > 200)),
    ("pending_qty", "What is the total `qty` summed over all orders with status 'pending'?",
     sum(o["qty"] for o in ORDERS if o["status"] == "pending")),
    ("avg_amount", "What is the average order `amount`, rounded to the nearest integer?",
     round(sum(o["amount"] for o in ORDERS) / len(ORDERS))),
    ("max_amount_id", "What is the `id` of the order with the highest `amount`?",
     max(ORDERS, key=lambda o: o["amount"])["id"]),
    ("count_c3", "How many orders have customer_id 'c3'?",
     sum(1 for o in ORDERS if o["customer_id"] == "c3")),
    ("west_shipped_total", "What is the total `amount` of orders that are in region 'West' AND status 'shipped'?",
     sum(o["amount"] for o in ORDERS if o["region"] == "West" and o["status"] == "shipped")),
    ("widget_total", "What is the total `amount` of all orders for product 'widget'?",
     sum(o["amount"] for o in ORDERS if o["product"] == "widget")),
    ("second_highest", "What is the second-highest order `amount`?",
     sorted((o["amount"] for o in ORDERS), reverse=True)[1]),
    ("top_product", "Which `product` appears in the most orders? Reply with the product name.",
     max(_orders_per_product().items(), key=lambda kv: kv[1])[0]),
    ("top_region_total", "Summing `amount` per region, what is the total of the region with the highest total?",
     max(_by_region_totals().values())),
    ("top_customer", "Which customer (by customer_id) has the highest total order `amount`? Reply with the id.",
     max(_cust_totals().items(), key=lambda kv: kv[1])[0]),
    # joins with get_customers
    ("gold_total", "Using both tools: what is the total order `amount` for customers whose `tier` is 'gold'?",
     sum(o["amount"] for o in ORDERS if _CUST[o["customer_id"]]["tier"] == "gold")),
    ("east_customers_orders", "Using both tools: how many orders belong to customers whose customer `region` is 'East'?",
     sum(1 for o in ORDERS if _CUST[o["customer_id"]]["region"] == "East")),
    ("silver_shipped_total", "Using both tools: total `amount` of 'shipped' orders placed by 'silver'-tier customers?",
     sum(o["amount"] for o in ORDERS if o["status"] == "shipped" and _CUST[o["customer_id"]]["tier"] == "silver")),
    ("customers_with_cancelled", "Using both tools: how many distinct customers have at least one 'cancelled' order?",
     len({o["customer_id"] for o in ORDERS if o["status"] == "cancelled"})),
    ("customers_no_orders", "Using both tools: how many customers have NO orders at all?",
     sum(1 for c in CUSTOMERS if c["id"] not in {o["customer_id"] for o in ORDERS})),
]


# --- tools (native for codemode, stringified for classic) -------------------
def _data_tools(stringify: bool) -> list[Tool]:
    def mk(name: str, desc: str, data: object) -> Tool:
        async def execute() -> object:
            return str(data) if stringify else data

        return ToolDef(execute, name=name, description=desc, parameters={}).as_tool()

    return [
        mk("get_orders",
           "Return all orders. Each order is a dict with keys: id, customer_id, product, amount, qty, status, region.",
           ORDERS),
        mk("get_customers",
           "Return all customers. Each customer is a dict with keys: id, name, tier, region.",
           CUSTOMERS),
    ]


@solver
def _set_tools(codemode: bool, force: bool) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        if codemode:
            state.tools = [run_code(tools=_data_tools(stringify=False))]
            if force:
                state.tool_choice = ToolFunction(name="run_code")
        else:
            state.tools = _data_tools(stringify=True)
        return state

    return solve


def _dataset() -> list[Sample]:
    return [Sample(input=instr, target=str(exp), id=tid) for tid, instr, exp in _TASKS]


@task
def synth(codemode: bool = False, force: bool = False) -> Task:
    steps = [system_message(SYSTEM)]
    if codemode:
        steps.append(system_message(STRONG_GUIDANCE if force else CODEMODE_GUIDANCE))
    steps += [_set_tools(codemode, force), generate(tool_calls="loop")]
    return Task(dataset=_dataset(), solver=chain(steps), scorer=m3_match(), name="synth_agg")
