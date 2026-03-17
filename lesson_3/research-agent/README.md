# Research Agent

Інтерактивний агент-дослідник, який шукає інформацію в інтернеті та генерує структуровані Markdown-звіти.

## Архітектура

```
main.py    — REPL-цикл (вхідна точка)
agent.py   — налаштування LLM, tools, memory, create_react_agent
tools.py   — реалізація інструментів (web_search, read_url, write_report)
config.py  — системний промпт, константи, налаштування
```

Агент побудований на **LangChain + LangGraph** з використанням `create_react_agent`.
Модель підключається через OpenAI-сумісний API (LM Studio).

## Інструменти

| Tool | Опис |
|------|------|
| `web_search` | Пошук через DuckDuckGo (ddgs) |
| `read_url` | Витягування тексту зі сторінки (trafilatura) |
| `write_report` | Збереження Markdown-звіту у файл |

## Встановлення

```bash
cd lesson_3/research-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

1. Запустіть LM Studio з моделлю `qwen3.5-35b-a3b` на `http://127.0.0.1:1234`
2. Запустіть агента:

```bash
python main.py
```

3. Введіть питання для дослідження, наприклад:

```
You: Порівняй три підходи до побудови RAG: naive, sentence-window та parent-child retrieval
```

Агент виконає пошук, прочитає релевантні сторінки та збереже звіт у `output/`.

## Приклад

Згенерований звіт — у `output/report.md`.
