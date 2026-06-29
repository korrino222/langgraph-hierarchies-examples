"""Deterministic expense parsing and formatting tools for the monolith agent."""

from __future__ import annotations

import json
import re
from typing import Annotated, Any
from uuid import uuid4

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

try:
    from langchain_core.tools import InjectedToolCallId
except ImportError:
    from langgraph.prebuilt import InjectedToolCallId  # type: ignore[no-redef]

_AMOUNT_RE = re.compile(r"\$?\s*([\d,]+\.\d{2})")
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _error(reason: str) -> dict[str, Any]:
    return {"status": "error", "stage": "extraction", "reason": reason}


def parse_expense(raw_text: str) -> dict[str, Any]:
    """Parse a single-line expense note into structured fields."""
    text = raw_text.strip()
    if not text:
        return _error("empty input")

    amount_match = _AMOUNT_RE.search(text)
    date_match = _DATE_RE.search(text)

    missing: list[str] = []
    if not amount_match:
        missing.append("amount")
    if not date_match:
        missing.append("date")

    parts = [part.strip() for part in text.split(",")]
    vendor = parts[1] if len(parts) > 1 else ""
    category = parts[-1] if len(parts) > 3 else ""

    if not vendor:
        missing.append("vendor")
    if not category or category == vendor:
        missing.append("category")

    if missing:
        return _error(f"missing: {', '.join(missing)}")

    amount = float(amount_match.group(1).replace(",", ""))
    return {
        "status": "ok",
        "vendor": vendor,
        "amount": amount,
        "date": date_match.group(1),
        "category": category,
    }


def format_expense(artifact: dict[str, Any] | str) -> dict[str, Any]:
    """Format a structured extraction artifact into a printable card."""
    if isinstance(artifact, str):
        try:
            artifact = json.loads(artifact)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "stage": "formatting",
                "reason": "invalid artifact JSON",
            }

    if artifact.get("status") != "ok":
        return {
            "status": "error",
            "stage": "formatting",
            "reason": "cannot format non-ok extraction artifact",
        }

    card = (
        f"{artifact['vendor']} | ${artifact['amount']:.2f} | "
        f"{artifact['date']} | {artifact['category']}"
    )
    return {"status": "ok", "card": card}


@tool
def extract_expense(
    raw_text: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Extract structured expense fields from raw text.

    Returns JSON with status ok (vendor, amount, date, category) or error.
    """
    result = parse_expense(raw_text)
    payload = json.dumps(result)
    return Command(
        update={
            "messages": [
                ToolMessage(content=payload, tool_call_id=tool_call_id, id=str(uuid4()))
            ],
        }
    )


@tool
def format_expense_card(
    extraction_json: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Format a structured extraction JSON artifact into a printable card."""
    result = format_expense(extraction_json)
    payload = result.get("card") or json.dumps(result)
    return Command(
        update={
            "messages": [
                ToolMessage(content=payload, tool_call_id=tool_call_id, id=str(uuid4()))
            ],
        }
    )
