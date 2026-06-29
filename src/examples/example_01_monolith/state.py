"""State schema for the monolith example."""

from __future__ import annotations

from langgraph_hierarchies.state.schema import BaseState


class MonolithState(BaseState):
    """Extended state carrying raw input for the monolith pipeline."""

    raw_input: str
