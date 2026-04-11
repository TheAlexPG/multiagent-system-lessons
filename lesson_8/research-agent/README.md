# Multi-Agent Research System (Lesson 8)

Мультиагентна дослідницька система з Supervisor, який координує трьох спеціалізованих суб-агентів.

## Архітектура

```
User (REPL)
  │
  ▼
Supervisor Agent
  ├── 1. plan(request)       → Planner Agent  → structured ResearchPlan
  ├── 2. research(plan)      → Research Agent  → findings from web + KB + project
  ├── 3. critique(findings)  → Critic Agent    → CritiqueResult (APPROVE/REVISE)
  │       ├── APPROVE → step 4
  │       └── REVISE  → back to step 2 (max 2 rounds)
  └── 4. save_report(...)    → HITL gate → user approve/edit/reject
```

## Що змінилось порівняно з lesson_5

| lesson_5 | lesson_8 |
|----------|----------|
| 1 Research Agent | Supervisor + 3 sub-agents (Planner, Researcher, Critic) |
| Single-pass research | Iterative: Critic can send back for revision |
| No approval flow | HITL: save_report requires user approval |
| Free text output | Planner/Critic return structured JSON (Pydantic) |
| Web + KB tools only | + `grep_search`, `glob_find`, `read_file` for project research |

## Інструменти

| Tool | Опис | Використовується |
|------|------|------------------|
| `web_search` | Пошук в інтернеті (DuckDuckGo) | Planner, Researcher, Critic |
| `read_url` | Читання веб-сторінок | Researcher |
| `knowledge_search` | Пошук в базі знань (PDF) | Planner, Researcher, Critic |
| `grep_search` | Пошук в файлах проєкту (regex) | Planner, Researcher, Critic |
| `glob_find` | Пошук файлів за патерном | Planner, Researcher |
| `read_file` | Читання файлу проєкту | Researcher |
| `save_report` | Збереження звіту (HITL) | Supervisor |

## Встановлення

```bash
cd lesson_8/research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ingest.py  # build RAG index from data/
```

## Запуск

```bash
python main.py
```

## LLM

- **Model**: google/gemma-4-26b-a4b
- **Endpoint**: LM Studio at http://192.168.0.146:11434/v1
- **Embeddings**: all-MiniLM-L6-v2 (local sentence-transformers)
- **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2 (local)
