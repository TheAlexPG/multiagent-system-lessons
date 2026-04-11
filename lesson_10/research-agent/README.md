# Multi-Agent Research System — Testing (Lesson 10)

Extension of Lesson 8 with comprehensive evaluation tests using [deepeval](https://github.com/confident-ai/deepeval).

## Architecture

```
User (REPL)
  |
  v
Supervisor Agent
  +-- 1. plan(request)       -> Planner Agent  -> structured ResearchPlan
  +-- 2. research(plan)      -> Research Agent  -> findings from web + KB + project
  +-- 3. critique(findings)  -> Critic Agent    -> CritiqueResult (APPROVE/REVISE)
  |       +-- APPROVE -> step 4
  |       +-- REVISE  -> back to step 2 (max 2 rounds)
  +-- 4. save_report(...)    -> HITL gate -> user approve/edit/reject
```

## What Lesson 10 Adds

| Component | Description |
|-----------|-------------|
| `tests/golden_dataset.json` | 15 test examples: 5 happy_path, 5 edge_cases, 5 failure_cases |
| `tests/test_planner.py` | Plan quality, structure, search query relevance |
| `tests/test_researcher.py` | Groundedness, completeness, multi-source usage |
| `tests/test_critic.py` | APPROVE vs REVISE correctness, actionable feedback |
| `tests/test_tools.py` | Tool correctness — which tools agents call |
| `tests/test_e2e.py` | End-to-end pipeline evaluation on golden dataset |
| `tests/conftest.py` | Shared fixtures, LocalLLM wrapper for deepeval |

## Setup

```bash
cd lesson_10/research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build RAG index (copy data/ from lesson_8 first)
python ingest.py
```

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test module
```bash
pytest tests/test_planner.py -v
pytest tests/test_researcher.py -v
pytest tests/test_critic.py -v
pytest tests/test_tools.py -v
pytest tests/test_e2e.py -v
```

### Run by category
```bash
# Only happy path e2e tests
pytest tests/test_e2e.py::TestE2EHappyPath -v

# Only edge case tests
pytest tests/test_e2e.py::TestE2EEdgeCases -v

# Only failure case tests
pytest tests/test_e2e.py::TestE2EFailureCases -v
```

### Run with deepeval dashboard
```bash
deepeval test run tests/test_planner.py
deepeval test run tests/test_e2e.py
```

### Run a single test
```bash
pytest tests/test_planner.py::TestPlannerStructuredOutput::test_plan_has_valid_json_structure -v
```

## Test Categories

### Planner Tests (`test_planner.py`)
- **Structure Quality**: Does the plan contain goal, search_queries, sources, output_format?
- **Query Relevance**: Are search queries relevant to the input question?
- **Source Selection**: Does the planner choose appropriate sources (KB, web, project)?
- **Multilingual**: Can it handle non-English queries?

### Researcher Tests (`test_researcher.py`)
- **Groundedness**: Are findings supported by cited sources?
- **Completeness**: Does research cover all aspects of the topic?
- **Multi-Source**: Does it use both knowledge base and web?

### Critic Tests (`test_critic.py`)
- **APPROVE**: Good research gets approved with strengths listed
- **REVISE**: Weak research gets sent back with specific revision requests
- **Actionable Feedback**: Revision requests are concrete, not vague

### Tool Correctness Tests (`test_tools.py`)
- **Planner Tools**: Calls search tools during planning
- **Researcher Tools**: Uses multiple tool types (>= 2)
- **Save Report**: Correct schema and workflow position

### End-to-End Tests (`test_e2e.py`)
- **Happy Path**: 5 standard AI/ML queries evaluated for relevance and quality
- **Edge Cases**: Ambiguous, multilingual, broad/narrow queries
- **Failure Cases**: Out-of-domain, nonsensical, inappropriate queries

## LLM Configuration

- **Model**: google/gemma-4-26b-a4b
- **Endpoint**: http://192.168.0.146:11434/v1
- **Deepeval metrics**: Use the same local model (LocalLLM wrapper in conftest.py)

## Notes

- Tests call the real LLM endpoint — they are integration tests, not mocks
- Each test may take 30-120 seconds depending on agent complexity
- E2E tests are the slowest (full plan-research-critique loop)
- Thresholds are set conservatively (0.3-0.6) for local models
- The `data/` and `vector_store/` directories must be populated before running tests
