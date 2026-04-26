# Multi-Agent Research System + Langfuse Observability (Lesson 12)

Extension of Lesson 10: Langfuse tracing, prompt management, and LLM-as-a-Judge evaluation.

## What Lesson 12 Adds

| Було (lesson 10) | Стало (lesson 12) |
|-------------------|-------------------|
| Система як чорна скринька | Кожен запуск — trace в Langfuse з повним деревом |
| DeepEval тести запускаються вручну | Langfuse автоматично оцінює traces через LLM-as-a-Judge |
| Промпти захардкоджені в config.py | Всі промпти в Langfuse Prompt Management |
| Немає session/user tracking | Traces згруповані по sessions, є user_id |

## Architecture

```
User (REPL) → main.py
  │  @observe(name="user_query")
  │  langfuse_context.update_current_trace(session_id, user_id)
  ▼
Supervisor Agent  ← prompt from Langfuse: "supervisor-agent"
  │  @observe(name="supervisor_turn")
  │  langfuse.openai.OpenAI (auto-traces all LLM calls)
  │
  ├── plan()      @observe → Planner   ← prompt: "planner-agent"
  ├── research()  @observe → Researcher ← prompt: "researcher-agent"
  ├── critique()  @observe → Critic     ← prompt: "critic-agent"
  └── save_report() → HITL gate

All LLM calls, tool executions, and agent spans appear
as a nested tree in Langfuse Tracing UI.
```

## Langfuse Integration Points

| Component | Integration |
|-----------|-------------|
| `langfuse_client.py` | Singleton Langfuse client + `get_prompt()` helper |
| `agents/base.py` | `langfuse.openai.OpenAI` wrapper + `@observe()` on `run()` and `_execute_tool()` |
| `supervisor.py` | `@observe(name="supervisor_turn")` + prompt from Langfuse |
| `agents/*.py` | `@observe(name="*_agent")` + prompts from Langfuse |
| `main.py` | `@observe(name="user_query")` + session_id/user_id tracking |
| `setup_prompts.py` | One-time script to push prompts to Langfuse |

## Setup

```bash
cd lesson_12/research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build RAG index
python ingest.py

# Push prompts to Langfuse Prompt Management (one-time)
python setup_prompts.py
```

## Running

```bash
python main.py
```

After 3-5 queries, check Langfuse UI:
- **Tracing → Traces** — full tree for each query
- **Sessions** — queries grouped by session
- **Users** — user tracking
- **Prompts** — all 4 agent prompts managed here
- **LLM-as-a-Judge → Evaluators** — automatic scores on new traces

## Langfuse LLM-as-a-Judge Evaluators

Set up in Langfuse UI (LLM-as-a-Judge → Evaluators → + Set up evaluator):

### Evaluator 1: Answer Relevancy (numeric 0-1)
Checks if the agent's final response is relevant to the user's question.

### Evaluator 2: Research Completeness (boolean)
Checks if the research covers all aspects of the question.

## Screenshots

After running, save 4 screenshots to `screenshots/`:
1. Trace tree (nested spans for a full query)
2. Session view (multiple traces in one session)
3. Evaluator scores (LLM-as-a-Judge results on traces)
4. Prompt Management (all 4 prompts)

## Configuration

- **LLM**: qwen/qwen3.6-27b via LM Studio (http://192.168.0.146:11434)
- **Langfuse**: cloud.langfuse.com
- **Embeddings**: all-MiniLM-L6-v2 (local)
- **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2 (local)
