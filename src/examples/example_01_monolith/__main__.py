"""CLI entry point for Example 01 — monolith agent."""

from __future__ import annotations

import argparse
import json

from langgraph_hierarchies.state.context import BaseContext
from langgraph_hierarchies.state.schema import create_base_state_defaults

from examples.example_01_monolith.agents import MONOLITH_GOAL, compile_root
from examples.example_01_monolith.model import (
    RuleBasedModel,
    create_openai_model,
    load_raw_text,
)
from examples.example_01_monolith.tracing import (
    apply_project_override,
    build_run_config,
    load_env,
    new_thread_id,
    print_tracing_hint,
)


def _llm_initial_state(raw_fixture: str) -> dict:
    raw_text = load_raw_text(raw_fixture)
    state = create_base_state_defaults()
    state["raw_input"] = raw_text
    state["current_agent_args"] = {
        "task": (
            "Extract and format this expense record.\n\n"
            f"{raw_text}"
        ),
        "task_scope": (
            "Use extract_expense, format_expense_card, and finish_task only. "
            "Do not skip steps when extraction succeeds."
        ),
        "task_iterations": 0,
    }
    return state


def _print_result(result: dict) -> None:
    report = result.get("current_agent_report", "")
    try:
        artifact = json.loads(report)
    except json.JSONDecodeError:
        if report:
            print(f"[Monolith]  card:      {report}")
        return

    if artifact.get("status") == "ok" and "card" in artifact:
        print(f"[Monolith]  card:      {artifact['card']}")
    elif artifact.get("status") == "error":
        print(f"[Monolith]  error:     {artifact.get('reason', artifact)}")
    else:
        print(json.dumps(artifact, indent=2))


def run_pipeline(
    *,
    ok: bool,
    use_llm: bool,
    project: str | None,
    thread_id: str,
) -> dict:
    mode = (
        "llm-ok"
        if use_llm and ok
        else "llm-fail"
        if use_llm
        else "scripted-ok"
        if ok
        else "scripted-fail"
    )
    project_name = apply_project_override(project)
    config = build_run_config(
        thread_id=thread_id,
        run_name=f"example-01-{mode}",
        tags=[mode],
    )

    root = compile_root()
    if use_llm:
        context = BaseContext(thread_id=thread_id, model=create_openai_model())
        raw_fixture = "raw_ok.txt" if ok else "raw_fail.txt"
        state = _llm_initial_state(raw_fixture)
    else:
        context = BaseContext(
            thread_id=thread_id,
            model=RuleBasedModel.for_ok() if ok else RuleBasedModel.for_fail(),
        )
        state = create_base_state_defaults()
        raw = load_raw_text("raw_ok.txt" if ok else "raw_fail.txt")
        state["raw_input"] = raw
        state["current_agent_args"] = {
            "task": f"Extract and format this expense record.\n\n{raw}",
            "task_scope": "Use extract_expense, format_expense_card, and finish_task only.",
            "task_iterations": 0,
        }

    print("[Monolith]  pipeline started")
    print(f"[Monolith]  goal:      \"{MONOLITH_GOAL}\"")
    print_tracing_hint(project_name, thread_id)

    result = root.invoke(state, config=config, context=context)
    print(f"[Monolith]  messages in context: {len(result.get('messages', []))}")
    _print_result(result)
    return result


def main(argv: list[str] | None = None) -> None:
    load_env()

    parser = argparse.ArgumentParser(description="Example 01 — monolith agent")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--scripted-ok",
        action="store_true",
        help="Run on raw_ok.txt (deterministic, no API key)",
    )
    group.add_argument(
        "--scripted-fail",
        action="store_true",
        help="Run on raw_fail.txt (structured error, no API key)",
    )
    group.add_argument(
        "--llm-ok",
        action="store_true",
        help="Run on raw_ok.txt with gpt-4o-mini (OPENAI_API_KEY)",
    )
    group.add_argument(
        "--llm-fail",
        action="store_true",
        help="Run on raw_fail.txt with gpt-4o-mini",
    )
    parser.add_argument(
        "--project",
        metavar="NAME",
        help="Override LANGCHAIN_PROJECT for LangSmith (default: langgraph-hierarchies-examples-01)",
    )
    args = parser.parse_args(argv)
    thread_id = new_thread_id()

    if args.scripted_ok:
        run_pipeline(ok=True, use_llm=False, project=args.project, thread_id=thread_id)
    elif args.scripted_fail:
        run_pipeline(ok=False, use_llm=False, project=args.project, thread_id=thread_id)
    elif args.llm_ok:
        run_pipeline(ok=True, use_llm=True, project=args.project, thread_id=thread_id)
    elif args.llm_fail:
        run_pipeline(ok=False, use_llm=True, project=args.project, thread_id=thread_id)


if __name__ == "__main__":
    main()
