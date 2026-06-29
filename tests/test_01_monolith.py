"""Tests for Example 01 — monolith agent."""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph_hierarchies.state.context import BaseContext
from langgraph_hierarchies.state.schema import create_base_state_defaults

from examples.example_01_monolith.agents import MONOLITH_GOAL, compile_root
from examples.example_01_monolith.model import RuleBasedModel, load_raw_text
from examples.example_01_monolith.tools import format_expense, parse_expense

pytestmark = [pytest.mark.scripted]


def _invoke_ok_pipeline() -> dict:
    root = compile_root()
    context = BaseContext(model=RuleBasedModel.for_ok())
    state = create_base_state_defaults()
    raw = load_raw_text("raw_ok.txt")
    state["raw_input"] = raw
    state["current_agent_args"] = {
        "task": f"Extract and format this expense record.\n\n{raw}",
        "task_scope": "Use extract_expense, format_expense_card, and finish_task only.",
        "task_iterations": 0,
    }
    return root.invoke(
        state,
        config=RunnableConfig(recursion_limit=50),
        context=context,
    )


def _invoke_fail_pipeline() -> dict:
    root = compile_root()
    context = BaseContext(model=RuleBasedModel.for_fail())
    state = create_base_state_defaults()
    raw = load_raw_text("raw_fail.txt")
    state["raw_input"] = raw
    state["current_agent_args"] = {
        "task": f"Extract and format this expense record.\n\n{raw}",
        "task_scope": "Use extract_expense, format_expense_card, and finish_task only.",
        "task_iterations": 0,
    }
    return root.invoke(
        state,
        config=RunnableConfig(recursion_limit=50),
        context=context,
    )


def _tool_names_in_messages(messages: list) -> list[str]:
    names: list[str] = []
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            names.extend(call["name"] for call in message.tool_calls)
    return names


def test_ok_pipeline_produces_card() -> None:
    result = _invoke_ok_pipeline()
    report = result["current_agent_report"]
    assert report == "XYZ Consulting | $87.50 | 2024-03-15 | business development"


def test_fail_pipeline_produces_error_no_format_call() -> None:
    result = _invoke_fail_pipeline()
    artifact = json.loads(result["current_agent_report"])

    assert artifact["status"] == "error"
    assert artifact["stage"] == "extraction"
    assert "missing" in artifact["reason"]

    tool_names = _tool_names_in_messages(result.get("messages", []))
    assert "format_expense_card" not in tool_names


def test_all_messages_in_single_context() -> None:
    result = _invoke_ok_pipeline()
    assert len(result.get("messages", [])) >= 6


def test_no_subgraphs() -> None:
    root = compile_root()
    assert root.compiled_subgraphs == []


def test_monolith_goal_is_single_sentence() -> None:
    assert MONOLITH_GOAL.endswith(".")


def test_parse_and_format_tools() -> None:
    raw = load_raw_text("raw_ok.txt")
    extraction = parse_expense(raw)
    formatted = format_expense(extraction)
    assert formatted["status"] == "ok"
    assert "XYZ Consulting" in formatted["card"]
