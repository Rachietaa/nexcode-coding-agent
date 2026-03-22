# NexCode — Project Planning Document

> A planning document outlining the architecture, components, and 
> implementation plan for NexCode, an autonomous CLI coding assistant.

---

## Table of Contents
- [Project Goal](#project-goal)
- [System Architecture Plan](#system-architecture-plan)
- [Component Implementation Plan](#component-implementation-plan)
- [MCP Server Plan](#mcp-server-plan)
- [RAG Server Plan](#rag-server-plan)
- [CLI Interface Plan](#cli-interface-plan)
- [Provider Abstraction Plan](#provider-abstraction-plan)
- [Implementation Timeline](#implementation-timeline)
- [Diagrams](#diagrams)
- [Dependencies](#dependencies)

---

## Project Goal

We plan to build **NexCode** — an autonomous command-line coding assistant 
that takes natural language instructions from a developer, reasons about a 
local codebase, and autonomously reads, edits, and executes code to complete 
tasks.

NexCode will **not** be a chatbot. It will operate as an autonomous agent. 
Given a task, it will decide what to do, act on the file system, observe the 
results, and keep going until the job is done.

---

## System Architecture Plan

We plan to build NexCode around five core components that each have a single 
responsibility:
```
User
 │
 ▼
CLI REPL  ──────────────────────────────────────────────────────────────
 │  (Rich-powered terminal, streaming, confirm/auto-execute modes)      │
 ▼                                                                      │
Agentic Loop (LangGraph ReAct)                                          │
 │  reason → select tool → execute → observe → repeat until done        │
 ▼                                                                      │
Provider Abstraction Layer                                              │
 │  (Groq / Anthropic / OpenAI / Ollama — same interface)               │
 ▼                                                                      │
MCP Client                                                              │
 │  discovers tools dynamically from all connected servers              │
 ├──► Filesystem MCP Server   (read/write/list files)                   │
 ├──► Tavily MCP Server       (web search)                              │
 └──► Custom RAG MCP Server   (vector DB query over library docs)       │
                                                                        │
 ◄──────────────────────────────────────── streamed response ───────────┘
```

---

## Component Implementation Plan

### 1. CLI REPL — `main.py`

We plan to build the terminal interface using the **Rich** library.

**What we plan to implement:**
- A REPL loop that accepts user input and passes it to the agent
- Real-time streaming of LLM responses token by token
- Display of every tool call with its arguments before it executes
- A spinner/status indicator while waiting for LLM or tool responses
- Syntax highlighting for code blocks in responses
- A `--auto` flag to toggle between confirmation mode and auto-execute mode
- Session history preserved across turns in the same session

**Confirmation mode behavior we plan to build:**
```
[Tool] write_file(path="utils.py", ...) → Confirm? [y/n]:
```

**Auto-execute mode behavior we plan to build:**
```
[Tool] write_file(path="utils.py", ...) → executing...
```

---

### 2. Agentic Loop — `agent/loop.py`

We plan to implement the agentic loop using **LangGraph's ReAct agent**.

**What we plan to implement:**
- A ReAct agent that reasons about the task, selects a tool, executes it, 
  observes the result, and loops until the task is complete
- Full conversation history passed to the LLM on every turn
- Tool results appended to context after each execution
- The loop terminates only when the LLM decides no more tools are needed

**Why LangGraph:** It handles the reason-act-observe cycle natively, supports 
tool calling across all LangChain providers, and makes agent state easy to 
inspect and debug.

---

### 3. Provider Abstraction — `agent/providers.py`

We plan to support **four LLM providers** behind a single unified interface.

**Providers we plan to support:**

| Provider | Type | Model | Notes |
|----------|------|-------|-------|
| Groq | Cloud | `llama-3.3-70b-versatile` | Fast inference, free tier |
| Anthropic | Cloud | `claude-sonnet-4-6` | Highest quality |
| OpenAI | Cloud | `gpt-4o` | Broad ecosystem |
| Ollama | Local | `llama3.2`, `codellama` | Offline, no API key |

**How we plan to switch providers:**
```bash
PROVIDER=groq nexcode
PROVIDER=anthropic nexcode
PROVIDER=ollama MODEL=codellama nexcode
```

The agentic loop will never touch provider-specific code — only the 
abstraction layer will.

---

### 4. MCP Client — `mcp_client/client.py`

We plan to use **LangChain's MultiServerMCPClient** to connect to all three 
MCP servers.

**What we plan to implement:**
- Connect to all three MCP servers on startup
- Discover and load all available tools dynamically — no hardcoded schemas
- Pass the full tool list to the LangGraph agent before each session
- Handle tool routing: the agent calls a tool by name, the client figures out 
  which server handles it

---

## MCP Server Plan

We plan to connect three MCP servers. All tools will be discovered dynamically 
at runtime.

### Server 1 — Filesystem (Official)

**Package:** `@modelcontextprotocol/server-filesystem`

**Tools we expect to use:**
- `read_file` — read any file in the project
- `write_file` — write or overwrite a file
- `list_directory` — list contents of a directory
- `create_directory` — create new folders

**Scope:** We plan to restrict the server to the project root directory to 
prevent the agent from accidentally modifying system files.

---

### Server 2 — Tavily (External Resource)

**Package:** `tavily-mcp`

**Tools we expect to use:**
- `web_search` — search the web for documentation, best practices, examples
- `web_fetch` — fetch the content of a specific URL

**When the agent will call this:** When it needs information not available in 
the local codebase — library changelogs, API references, current best 
practices.

---

### Server 3 — Custom RAG Server (Our Own)

**What we plan to build:** A locally-running FastMCP server that lets the 
agent query a vector database of library documentation.

**Why we are building this ourselves:** To gain experience building an MCP 
server rather than just consuming one, and to implement an advanced RAG 
technique on top of it.

**Tool we plan to expose:**
```python
@mcp.tool()
def rag_query(query: str) -> str:
    """Query the local vector database for relevant documentation chunks."""
```

---

## RAG Server Plan

### Ingestion Pipeline (runs once)

We plan to build the following one-time setup pipeline:
```
Step 1 — Load documents
         └─► Read all .md and .txt files from /docs folder

Step 2 — Chunk documents
         └─► Semantic chunking (split on content boundaries, 
             not fixed character counts)

Step 3 — Embed chunks
         └─► sentence-transformers (runs locally, no API key needed)

Step 4 — Store in vector database
         └─► ChromaDB persistent client
             (survives restarts — no re-embedding needed)
```

After this runs once, all future sessions will query the existing database 
directly.

### Advanced RAG Technique — HyDE

We plan to implement **Hypothetical Document Embeddings (HyDE)** as our 
advanced retrieval technique.

**The problem we are solving:**  
A query like *"how do I use LCEL with streaming?"* uses different vocabulary 
than the documentation that answers it. Embedding the raw query often misses 
the best chunks.

**How HyDE works:**
```
Standard RAG (what we are NOT doing):
  query → embed query → search → chunks → answer

HyDE (what we ARE doing):
  query → LLM generates hypothetical answer
        → embed hypothetical answer
        → search vector DB
        → retrieve REAL matching chunks
        → return real chunks to agent
```

**Why we chose HyDE:**
- Directly fixes the vocabulary mismatch problem in technical doc queries
- Reuses the same LLM already powering the agent — no extra infrastructure
- Better retrieval quality for code-related questions than raw query embedding
- Simpler to implement than Fusion Retrieval (which requires multiple queries)

---

## CLI Interface Plan

We plan the terminal to look and behave like this:
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

## Implementation Timeline

We plan to build NexCode in the following order:

| Phase | What we plan to build | Why this order |
|-------|----------------------|----------------|
| **Phase 1** | Project structure, `requirements.txt`, `README.md` | Foundation before any code |
| **Phase 2** | Provider abstraction layer | Everything else depends on this |
| **Phase 3** | Basic agentic loop (no tools yet) | Verify LLM works before adding tools |
| **Phase 4** | MCP client + filesystem server | First real tool capability |
| **Phase 5** | Tavily external server | Second MCP server |
| **Phase 6** | RAG ingestion pipeline + ChromaDB | Build before the server |
| **Phase 7** | Custom RAG MCP server + HyDE | Third MCP server |
| **Phase 8** | CLI REPL with Rich, streaming, confirmation mode | Polish the interface |
| **Phase 9** | Testing, cleanup, comments, final README | Before submission |

---

## Diagrams

> All diagrams are in the [`/docs`](./docs) folder.

| Diagram | File | What it shows |
|---------|------|---------------|
| **State Diagram** | `docs/state_diagram.png` | Full NexCode session lifecycle — Idle → Input → LLM → Tool loop → Complete |
| **Sequence Diagram 1** | `docs/sequence_diagram_1.png` | Documentation query — RAG server invoked end-to-end |
| **Sequence Diagram 2** | `docs/sequence_diagram_2.png` | File read + web search + file edit with confirmation |

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

**Environment variables needed**
```bash
GROQ_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...        # optional
TAVILY_API_KEY=...
```
