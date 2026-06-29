"""Graph classes for the monolith example."""

from __future__ import annotations

from typing import Any

from langgraph_hierarchies.graphs.react import ReactGraph
from langgraph_hierarchies.state.context import BaseContext
from langgraph_hierarchies.state.schema import create_base_state_defaults
from langgraph_hierarchies.tools.builtins import finish_task

from examples.example_01_monolith.state import MonolithState
from examples.example_01_monolith.tools import extract_expense, format_expense_card

MONOLITH_GOAL = (
    "Extract and format an expense record from raw text in a single context."
)
MONOLITH_SYSTEM = (
    "You are a single expense-processing agent. The raw expense text is in your task.\n"
    "Steps:\n"
    "1. Call extract_expense with the full raw text.\n"
    "2. If extraction status is 'ok', call format_expense_card with the extraction JSON.\n"
    "   If status is 'error', skip formatting and go directly to step 3.\n"
    "3. Call finish_task with the formatted card text or the error JSON.\n"
    "Never call raise_exception. Always complete with finish_task.\n"
    "Call exactly one tool per step."
)


class MonolithRoot(ReactGraph):
    """Single agent that extracts and formats an expense in one flat context."""

    name = "monolith_root"
    description = MONOLITH_GOAL

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tools = [t for t in self.tools if getattr(t, "name", None) != "raise_exception"]


def compile_root() -> Any:
    """Compile the monolith root graph without subagent_policy or subgraphs."""
    root = MonolithRoot(
        state_schema=MonolithState,
        context_schema=BaseContext,
        reports_to_supervisor=False,
        message_system=MONOLITH_SYSTEM,
        message_reasoning="Which tool should I call next?",
        tools=[finish_task, extract_expense, format_expense_card],
    )
    return root.compile_as_root(state_defaults=create_base_state_defaults())
