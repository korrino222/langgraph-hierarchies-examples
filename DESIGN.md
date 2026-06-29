# DESIGN.md

Design notes for `langgraph-hierarchies-examples`. Maps runnable exhibits to the article ladder.

## Example 01 — Monolith

**Article:** [Decomposability in AI workflows](https://medium.com/@ishish222/decomposability-in-ai-workflows-what-it-is-and-why-you-want-it-c12c9a939565) — the “before” picture: one agent, one flat context.

**Run (no API key):**

```bash
uv run python -m examples.example_01_monolith --scripted-ok
uv run python -m examples.example_01_monolith --scripted-fail
```

**Run with real LLM:**

```bash
cp .env.example .env   # set OPENAI_API_KEY
uv run python -m examples.example_01_monolith --llm-ok
uv run python -m examples.example_01_monolith --llm-fail
```

**LangSmith tracing:**

```bash
cp .env.example .env   # set LANGCHAIN_TRACING_V2=true, LANGCHAIN_API_KEY, LANGCHAIN_PROJECT
uv run python -m examples.example_01_monolith --scripted-ok
# Open https://smith.langchain.com → project langgraph-hierarchies-examples-01
# Filter by tag: example-01, scripted-ok | llm-ok | llm-fail
```

Optional: `--project my-traces` overrides `LANGCHAIN_PROJECT` for a single run.

### What the reader should see

| Signal | Where in code |
|--------|---------------|
| **Single goal** | `MONOLITH_GOAL` in [`agents.py`](src/examples/example_01_monolith/agents.py); printed in CLI |
| **Flat context** | No subgraphs, no `SubchainPolicy`; CLI prints `messages in context: N` |
| **Same task** | Same fixtures as example 02 (`raw_ok.txt`, `raw_fail.txt`) |
| **Failure path** | `format_expense_card` never called on bad input; `test_fail_pipeline_produces_error_no_format_call` |

### Graph topology

```
MonolithRoot (ReactGraph, no subchain_policy, no subgraphs)
    tools: extract_expense, format_expense_card, finish_task
```

Every reasoning turn and tool result stays in one `messages` list. Compare with example 02, where child agents enter with `messages=[]`.

### LangSmith: what to verify

| Mode | Run name | Tags | What to look for |
|------|----------|------|------------------|
| `--scripted-ok` | `example-01-scripted-ok` | `example-01`, `scripted-ok` | Single flat span; no nested extractor/formatter subgraphs |
| `--scripted-fail` | `example-01-scripted-fail` | `example-01`, `scripted-fail` | Extract + finish only; no format tool call |
| `--llm-ok` | `example-01-llm-ok` | `example-01`, `llm-ok` | LLM tool loop in one agent |
| `--llm-fail` | `example-01-llm-fail` | `example-01`, `llm-fail` | Structured error without formatting step |

---

## Example 02 — Artifact handoff

**Article:** [Decomposability in AI workflows](https://medium.com/@ishish222/decomposability-in-ai-workflows-what-it-is-and-why-you-want-it-c12c9a939565)

**Run (no API key):**

```bash
uv run python -m examples.example_02_artifact_handoff --scripted-ok
uv run python -m examples.example_02_artifact_handoff --replay src/examples/example_02_artifact_handoff/fixtures/extraction_artifact.json
```

**Run with real LLM** (orchestration at root only; child units stay deterministic):

```bash
cp .env.example .env   # set OPENAI_API_KEY
uv run python -m examples.example_02_artifact_handoff --llm-ok
uv run python -m examples.example_02_artifact_handoff --llm-fail
```

**LangSmith tracing** (works for scripted, LLM, and replay modes):

```bash
cp .env.example .env   # set LANGCHAIN_TRACING_V2=true, LANGCHAIN_API_KEY, LANGCHAIN_PROJECT
uv run python -m examples.example_02_artifact_handoff --scripted-ok
# Open https://smith.langchain.com → project langgraph-hierarchies-examples-02
# Filter by tag: example-02, scripted-ok | llm-ok | replay
```

Optional: `--project my-traces` overrides `LANGCHAIN_PROJECT` for a single run.

### Four decomposability tests → code

| Test | What the reader should see | Where in code |
|------|---------------------------|---------------|
| **Goal** | Each unit has a one-sentence purpose with no cross-reference | `EXTRACTOR_GOAL` / `FORMATTER_GOAL` in [`agents.py`](src/examples/example_02_artifact_handoff/agents.py); printed in CLI trace |
| **Boundary** | Child enters with `messages=[]`; parent history unchanged; only `pipeline_artifact` merges back | `ARTIFACT_POLICY` in [`policy.py`](src/examples/example_02_artifact_handoff/policy.py); `test_boundary_ok` in [`tests/test_02_artifact_handoff.py`](tests/test_02_artifact_handoff.py) |
| **Failure** | Bad input → structured error artifact; Formatter never invoked | `parse_expense()` in [`tools.py`](src/examples/example_02_artifact_handoff/tools.py); `RuleBasedModel.for_fail()` in [`model.py`](src/examples/example_02_artifact_handoff/model.py); `test_failure_structured` |
| **Replay** | Formatter runs from committed fixture; output matches full pipeline | `--replay` in [`__main__.py`](src/examples/example_02_artifact_handoff/__main__.py); `test_replay_matches_pipeline` |

### Graph topology

```
HandoffRoot (ReactGraph, no subchain_policy)
  ├── Extractor (SimpleGraph, ARTIFACT_POLICY)
  └── Formatter (SimpleGraph, ARTIFACT_POLICY)
```

Root orchestrates via subgraph tool calls. Children clear `messages` on entry and merge only `pipeline_artifact` on exit — the article's “context stays lean” primitive in miniature.

In `--llm-*` modes, **only the root** uses `gpt-4o-mini` for delegation decisions; Extractor and Formatter remain deterministic `SimpleGraph` workers. LangSmith traces show nested `handoff_root` → `extractor` / `formatter` spans either way.

### LangSmith: what to verify

| Mode | Run name | Tags | What to look for |
|------|----------|------|------------------|
| `--scripted-ok` | `example-02-scripted-ok` | `example-02`, `scripted-ok` | Nested extractor → formatter; child inputs have empty message history |
| `--scripted-fail` | `example-02-scripted-fail` | `example-02`, `scripted-fail` | Extractor only; no formatter child |
| `--llm-ok` | `example-02-llm-ok` | `example-02`, `llm-ok` | Root LLM turns + same subgraph nesting as scripted |
| `--replay` | `example-02-replay` | `example-02`, `replay` | Formatter span only |

### Deferred to later examples

- **Flat context at N items** → Example 03 / IRS matching stage
- **Monolith vs decomposed metrics** → IRS capstone (04)
