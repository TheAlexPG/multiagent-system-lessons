# Research Agent v3 — RAG + Hybrid Search + Reranking

Розширення Research Agent: додано RAG-інструмент з гібридним пошуком (semantic + BM25) та cross-encoder reranking.

## Що змінилось порівняно з lesson_4

| lesson_4 | lesson_5 |
|----------|----------|
| Tools: web_search, read_url, write_report | + `knowledge_search` (RAG tool) |
| Пошук лише в інтернеті | Пошук в інтернеті + локальна база знань |
| — | Ingestion pipeline (документи → чанки → embeddings → FAISS) |
| — | Hybrid search: semantic (FAISS) + BM25 |
| — | Cross-encoder reranking |

## Архітектура

```
main.py          — REPL-цикл
agent.py         — ResearchAgent (custom ReAct loop)
tools.py         — knowledge_search, web_search, read_url, write_report
retriever.py     — HybridRetriever: FAISS + BM25 + cross-encoder reranking
ingest.py        — Ingestion pipeline: docs → chunks → embeddings → vector store
config.py        — system prompt, tool schemas, налаштування
data/            — документи для завантаження (PDF, TXT, MD)
vector_store/    — FAISS index + метадані (створюється після ingest)
output/          — згенеровані звіти
```

### RAG Pipeline

```
1. Ingestion (python ingest.py):
   data/*.pdf,txt → RecursiveCharacterTextSplitter → SentenceTransformer → FAISS

2. Retrieval (knowledge_search tool):
   query → [Semantic: FAISS cosine] + [BM25: keyword match]
         → Merge (weighted fusion)
         → Cross-encoder reranking
         → Top-5 results
```

## Встановлення

```bash
cd lesson_5/research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

### 1. Завантажте документи в базу знань

Покладіть PDF/TXT/MD файли в `data/`, потім:

```bash
python ingest.py
```

### 2. Запустіть агента

```bash
python main.py
```

### Приклад

```
You: Що таке RAG і які є підходи до retrieval?

  🔧 Tool call: knowledge_search({"query": "RAG retrieval approaches"})
  📎 Result: Found 5 relevant passage(s): ...

  🔧 Tool call: web_search({"query": "RAG retrieval techniques 2024"})
  📎 Result: [{"title": "...", ...}]

  🔧 Tool call: write_report({"filename": "rag_approaches.md", ...})
  📎 Result: Report saved to output/rag_approaches.md

Agent: Звіт збережено. RAG — це техніка, де...
```

## Моделі

- **LLM**: qwen3.5-35b-a3b (LM Studio, http://127.0.0.1:1234)
- **Embeddings**: all-MiniLM-L6-v2 (sentence-transformers, локально)
- **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2 (локально)
