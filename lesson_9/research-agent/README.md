# Multi-Agent Research System (Lesson 9) -- MCP + ACP

Extension of Lesson 8: the same Supervisor / Planner / Researcher / Critic architecture,
but now tools are exposed over **MCP** (Model Context Protocol) and agents are
exposed over **ACP** (Agent Communication Protocol).

## Architecture

```
User (REPL)
  |
  v
main.py  -->  Supervisor (local, OpenAI SDK)
                  |
                  |--- ACP client --->  ACP Server (:8903)
                  |                       |-- planner agent
                  |                       |-- researcher agent
                  |                       |-- critic agent
                  |                       |       |
                  |                       |       +-- MCP client --> SearchMCP (:8901)
                  |                       |                           |-- web_search
                  |                       |                           |-- read_url
                  |                       |                           |-- knowledge_search
                  |                       |                           |-- grep_search
                  |                       |                           |-- glob_find
                  |                       |                           |-- read_file
                  |                       |                           +-- resource://knowledge-base-stats
                  |                       |
                  |--- MCP client --->  ReportMCP (:8902)
                                          |-- save_report  (HITL gate)
                                          +-- resource://output-dir
```

### Flow

1. User enters a question in the REPL (`main.py`)
2. **Supervisor** (local) plans the workflow using LLM tool calling
3. Supervisor calls **planner** / **researcher** / **critic** via ACP (`acp_server.py`)
4. Each ACP agent connects to **SearchMCP** via MCP client to use research tools
5. When the report is ready, Supervisor calls **ReportMCP** via MCP client
6. `save_report` goes through a HITL gate (approve / edit / reject)

## What changed vs Lesson 8

| Lesson 8 | Lesson 9 |
|----------|----------|
| Tools called directly (in-process) | Tools exposed via **MCP servers** (SearchMCP, ReportMCP) |
| Sub-agents called directly (in-process) | Sub-agents exposed via **ACP server** |
| Single process | 4 processes: SearchMCP, ReportMCP, ACP server, main |
| No protocol boundary | Clean protocol separation: MCP for tools, ACP for agents |

## Tools

| Tool | Description | MCP Server | Used By |
|------|-------------|------------|---------|
| `web_search` | Internet search (DuckDuckGo) | SearchMCP | Planner, Researcher, Critic |
| `read_url` | Read webpage content | SearchMCP | Researcher |
| `knowledge_search` | Search PDF knowledge base (RAG) | SearchMCP | Planner, Researcher, Critic |
| `grep_search` | Search project files by regex | SearchMCP | Planner, Researcher, Critic |
| `glob_find` | Find project files by pattern | SearchMCP | Planner, Researcher |
| `read_file` | Read project file contents | SearchMCP | Researcher |
| `save_report` | Save Markdown report (HITL) | ReportMCP | Supervisor |

The `grep_search`, `glob_find`, and `read_file` tools enable researching project files --
agents can explore the codebase, find config files, read source code, etc.

## Resources

| Resource URI | MCP Server | Description |
|--------------|------------|-------------|
| `resource://knowledge-base-stats` | SearchMCP | KB chunk count, sources, index status |
| `resource://output-dir` | ReportMCP | Output directory path, existing reports |

## Setup

```bash
cd lesson_9/research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build RAG index (put PDFs in data/ first)
python ingest.py
```

## Launch Order

Start each in a separate terminal (or use tmux/screen):

```bash
# Terminal 1: Search MCP server
python mcp_servers/search_mcp.py

# Terminal 2: Report MCP server
python mcp_servers/report_mcp.py

# Terminal 3: ACP server (agents)
python acp_server.py

# Terminal 4: Main REPL
python main.py
```

## Ports

| Service | Port | Protocol |
|---------|------|----------|
| SearchMCP | 8901 | MCP (SSE) |
| ReportMCP | 8902 | MCP (SSE) |
| ACP Server | 8903 | ACP (HTTP) |

## LLM

- **Model**: google/gemma-4-26b-a4b
- **Endpoint**: LM Studio at http://192.168.0.146:11434/v1
- **Embeddings**: all-MiniLM-L6-v2 (local sentence-transformers)
- **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2 (local)

## File Structure

```
lesson_9/research-agent/
  config.py              -- settings, prompts, ports
  schemas.py             -- Pydantic models
  ingest.py              -- PDF ingestion pipeline
  retriever.py           -- hybrid RAG retriever
  mcp_utils.py           -- MCP-to-OpenAI tool conversion
  mcp_servers/
    search_mcp.py        -- SearchMCP server (tools + resource)
    report_mcp.py        -- ReportMCP server (save + resource)
  acp_server.py          -- ACP server with 3 agents
  supervisor.py          -- local supervisor (ACP + MCP client)
  main.py                -- REPL entry point
  data/                  -- PDF documents for RAG
  vector_store/          -- FAISS index + metadata
  output/                -- saved reports
```
