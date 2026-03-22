# NexCode — Project Planning Document

> Blueprint for NexCode, an autonomous CLI coding assistant built on a 
> ReAct agentic loop with MCP tool integration and HyDE-powered RAG retrieval.

---

## Table of Contents
- [Project Goal](#project-goal)
- [System Architecture](#system-architecture)
- [Components](#components)
- [MCP Servers](#mcp-servers)
- [RAG Server](#rag-server)
- [CLI Interface](#cli-interface)
- [Provider Abstraction](#provider-abstraction)
- [Implementation Order](#implementation-order)
- [Diagrams](#diagrams)
- [Dependencies](#dependencies)

---

## Project Goal

**NexCode** is an autonomous command-line coding assistant. Given a natural 
language task, it reasons about a local codebase, selects tools, executes 
them, observes the results, and loops until the job is done.

This is not a chatbot. The agent decides what to do, acts on the file system, 
and keeps going without constant user input.

---

## System Architecture

Five core components:
```
User
 │
 ▼
CLI REPL
 │  Rich-powered terminal, streaming, confirm/auto-execute modes
 ▼
Agentic Loop (LangGraph ReAct)
 │  reason → select tool → execute → observe → repeat until done
 ▼
Provider Abstraction Layer
 │  Groq / Anthropic / OpenAI / Ollama — same interface for all
 ▼
MCP Client
 │  discovers tools dynamically from all connected servers
 ├──► Filesystem MCP Server   (read/write/list files)
 ├──► Tavily MCP Server       (web search)
 └──► Custom RAG MCP Server   (vector DB query over library docs)
```
File structure:
```
nexcode-coding-agent/
│
├── main.py                        ← CLI REPL entry point 
├── README.md                      ← setup and usage instructions
├── PLANNING.md                    ← project planning and architecture blueprint
├── requirements.txt               ← all Python dependencies
├── .env                           ← API keys 
├── .gitignore
│
├── planning/
│   ├── architecture.md            ← architecture overview and design decisions
│   ├── state_diagram.png          ← UML state machine diagram
│   ├── sequence_diagram_1.png     ← docs query scenario (RAG server)
│   └── sequence_diagram_2.png     ← file edit scenario (filesystem + Tavily)
│
├── config/
│   ├── __init__.py
│   └── settings.py                ← environment variables, provider config
│
├── agent/
│   ├── __init__.py
│   ├── loop.py                    ← LangGraph ReAct agentic loop
│   └── providers.py               ← Groq / Anthropic / OpenAI / Ollama abstraction
│
├── mcp_client/
│   ├── __init__.py
│   └── client.py                  ← MultiServerMCPClient, connects all 3 servers
│
├── tools/
│   ├── __init__.py
│   └── executor.py                ← tool execution handler, confirmation logic
│
├── rag_server/
│   ├── __init__.py
│   ├── ingest.py                  ← one-time ingestion pipeline (chunk, embed, store)
│   ├── retriever.py               ← HyDE retrieval logic
│   └── server.py                  ← FastMCP server, exposes rag_query tool
│
└── docs_source/                   ← library documentation files to embed (.md / .txt)

```

---

## Components

### 1. CLI REPL 

Built with the **Rich** library.

- REPL loop that accepts user input and passes it to the agent
- Real-time streaming of LLM responses token by token
- Every tool call displayed with its arguments before execution
- Spinner during LLM inference and tool execution
- Syntax highlighting for code blocks
- `--auto` flag toggles between confirmation and auto-execute mode
- Conversation history preserved across turns

---

### 2. Agentic Loop 

Built with **LangGraph ReAct**.

- Reason about the task, select a tool, execute it, observe the result, loop
- Full conversation history passed to the LLM on every turn
- Tool results appended to context after each execution
- Loop terminates only when the LLM decides no more tools are needed

**Why LangGraph:** Handles the reason-act-observe cycle natively, supports 
tool calling across all LangChain providers, graph-based state is easy to 
debug.

---

### 3. Provider Abstraction 

Four LLM providers behind one unified interface.

| Provider | Type | Model | Notes |
|----------|------|-------|-------|
| **Groq** | Cloud | `llama-3.3-70b-versatile` | Fast inference, free tier |
| **Anthropic** | Cloud | `claude-sonnet-4-6` | Highest quality |
| **OpenAI** | Cloud | `gpt-4o` | Broad ecosystem |
| **Ollama** | Local | `llama3.2`, `codellama` | Offline, no API key |

Switch with an environment variable — no code changes needed:
```bash
PROVIDER=groq nexcode
PROVIDER=anthropic nexcode
PROVIDER=ollama MODEL=codellama nexcode
```

---

### 4. MCP Client 

Uses **LangChain's MultiServerMCPClient**.

- Connects to all three MCP servers on startup
- Discovers and loads all tools dynamically — no hardcoded schemas
- Full tool list passed to the LangGraph agent before each session
- Routes tool calls to the correct server automatically

---

## MCP Servers

### Server 1 — Filesystem (Official)

**Package:** `@modelcontextprotocol/server-filesystem`

Tools: `read_file`, `write_file`, `list_directory`, `create_directory`

Scoped to the project root directory to prevent accidental system file 
modification.

---

### Server 2 — Tavily (External Resource)

**Package:** `tavily-mcp`

Tools: `web_search`, `web_fetch`

Called when the agent needs information not in the local codebase — 
library docs, API references, current best practices.

---

### Server 3 — Custom RAG Server

A locally-running FastMCP server for querying a vector database of library 
documentation.

Tool exposed:
```python
@mcp.tool()
def rag_query(query: str) -> str:
    """Query the local vector database for relevant documentation chunks."""
```

---

## RAG Server

### Ingestion Pipeline (one-time setup)
```
Step 1 — Load documents
         └─► .md and .txt files from /docs folder

Step 2 — Chunk
         └─► Semantic chunking (content boundaries, not fixed char counts)

Step 3 — Embed
         └─► sentence-transformers (local, no API key)

Step 4 — Store
         └─► ChromaDB persistent client (survives restarts)
```

Run once. All future sessions query the existing database — no re-embedding.

---

### Advanced RAG — HyDE

**Hypothetical Document Embeddings (HyDE)** is the retrieval technique.

**The problem:**  
A query like *"how do I use LCEL with streaming?"* uses different vocabulary 
than the documentation that answers it. Embedding the raw query misses the 
best chunks.

**The solution:**
```
Standard RAG:
  query → embed query → search → chunks → answer

HyDE:
  query → LLM generates hypothetical answer
        → embed hypothetical answer
        → search ChromaDB
        → retrieve REAL matching chunks
        → return to agent
```

**Why HyDE:**
- Fixes vocabulary mismatch in technical doc queries
- Reuses the same LLM already in the agent — no extra infrastructure
- Better retrieval than raw query embedding for code questions
- Simpler than Fusion Retrieval (no multiple queries needed)

---

## CLI Interface

Target terminal experience:
```
$ nexcode
╔══════════════════════════════════════════════════╗
║  NexCode v1.0                                    ║
║  Provider: groq  │  Model: llama-3.3-70b         ║
║  Mode: confirm                                   ║
╚══════════════════════════════════════════════════╝

You: Refactor utils.py to use proper error handling

  ⚙  [Tool] read_file(path="utils.py")
  ⚙  [Tool] web_search(query="Python error handling best practices")
  ⚙  [Tool] write_file(path="utils.py", content="...") → Confirm? [y/n]: y

✓ Done. Refactored utils.py — added try/except blocks, custom exception
  classes, and logging. All 12 functions updated.

You:
```

---

## Implementation Order

| Phase | What gets built | Why this order |
|-------|----------------|----------------|
| **1** | Project structure, `requirements.txt`, README | Foundation first |
| **2** | Provider abstraction layer | Everything else depends on this |
| **3** | Basic agentic loop (no tools yet) | Verify LLM works before adding tools |
| **4** | MCP client + filesystem server | First real tool capability |
| **5** | Tavily external server | Second MCP server |
| **6** | RAG ingestion pipeline + ChromaDB | Build the DB before the server |
| **7** | Custom RAG MCP server + HyDE | Third MCP server |
| **8** | CLI REPL — Rich, streaming, confirmation mode | Polish the interface |
---

## Diagrams

| Diagram | File | Description |
|---------|------|-------------|
| **State Diagram** | `planning/state_diagram.png` | Full session lifecycle — Idle → Input → LLM → Tool loop → Complete |
| **Sequence Diagram 1** | `planning/sequence_diagram_1.png` | Documentation query — RAG server invoked end-to-end |
| **Sequence Diagram 2** | `planning/sequence_diagram_2.png` | File read + web search + file edit with confirmation |

---

## Dependencies

**Python — `requirements.txt`**
```
langchain
langgraph
langchain-groq
langchain-anthropic
langchain-openai
langchain-ollama
chromadb
sentence-transformers
fastmcp
mcp
rich
tavily-python
```

**Node**
```
@modelcontextprotocol/server-filesystem
tavily-mcp
```

**Environment variables**
```bash
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...      
TAVILY_API_KEY=...
```
