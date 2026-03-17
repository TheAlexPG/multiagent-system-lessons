# Research Agent v2 — Custom ReAct Loop

Розширення Research Agent з lesson_3: `create_react_agent` замінено на власну реалізацію ReAct-циклу.

## Що змінилось порівняно з lesson_3

| lesson_3 | lesson_4 |
|----------|----------|
| `create_react_agent` (LangGraph) | Власний ReAct loop в `agent.py` |
| LangChain керує циклом | Ми самі керуємо циклом |
| `@tool` декоратор | Tools як JSON Schema для OpenAI API |
| `MemorySaver` для пам'яті | Власний список `messages` |
| `langchain`, `langgraph` залежності | Тільки `openai` SDK |
| Базовий system prompt | Покращений prompt з техніками промптингу |

## Архітектура

```
main.py    — REPL-цикл (вхідна точка)
agent.py   — ResearchAgent клас з власним ReAct loop
tools.py   — реалізація інструментів (plain functions + registry)
config.py  — system prompt, tool schemas (JSON), налаштування
```

### ReAct Loop (`agent.py`)

```
User message → append to messages
         ↓
   ┌─→ LLM call (messages + tool schemas)
   │        ↓
   │   Has tool_calls? ──No──→ Return final answer
   │        │ Yes
   │        ↓
   │   Execute each tool call
   │   Append tool results to messages
   │   Log: 🔧 tool name + args, 📎 result preview
   │        ↓
   └────────┘  (repeat until final answer or max_iterations)
```

## Встановлення

```bash
cd lesson_4/research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

1. Запустіть LM Studio з моделлю `qwen3.5-35b-a3b` на `http://127.0.0.1:1234`
2. Запустіть агента:

```bash
python main.py
```

## Приклад виводу

```
You: Порівняй naive RAG та sentence-window retrieval

  🔧 Tool call: web_search({"query": "naive RAG approach explained"})
  📎 Result: [{"title": "...", "url": "...", "snippet": "..."}...]

  🔧 Tool call: read_url({"url": "https://example.com/rag-comparison"})
  📎 Result: [5000 chars] Article about RAG approaches...

  🔧 Tool call: write_report({"filename": "rag_comparison.md", "content": "# ..."})
  📎 Result: Report saved to output/rag_comparison.md

Agent: Звіт збережено у output/rag_comparison.md. Ось основні відмінності: ...
```

## Приклад звіту

Згенерований звіт — у `output/report.md`.
