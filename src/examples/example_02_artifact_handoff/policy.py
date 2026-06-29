"""Subagent policy for artifact-only handoff."""

from langgraph_hierarchies.graphs.compiled import SubagentPolicy

ARTIFACT_POLICY = SubagentPolicy(
    clear_messages=True,
    merge_fields=["pipeline_artifact"],
)
