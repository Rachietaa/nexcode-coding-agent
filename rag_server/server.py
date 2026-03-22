import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastmcp import FastMCP
from config.settings import CHROMA_DB_PATH

mcp = FastMCP(
    name="NexCode RAG Server",
    instructions="Search local documentation using HyDE retrieval and return citation-aware results.",
)


@mcp.tool()
def query_documentation(query: str) -> str:
    if not os.path.exists(CHROMA_DB_PATH):
        return "Vector DB not found. Run: python rag_server/ingest.py first."

    try:
        print("RAG: query_documentation called", file=sys.stderr, flush=True)

        from rag_server.retriever import hyde_retrieve_with_citations, format_citation_context

        print("RAG: running retrieval", file=sys.stderr, flush=True)
        results = hyde_retrieve_with_citations(query)
        print(f"RAG: retrieved {len(results)} chunks", file=sys.stderr, flush=True)

        if not results:
            return (
                "You are answering using local documentation only.\n"
                "No relevant documentation was found.\n"
                "If asked to answer, say: I could not find that in the local documentation."
            )

        context = format_citation_context(results)
        print("RAG: context formatted, returning to agent", file=sys.stderr, flush=True)

        return f"""You are answering a question using local documentation only.

Instructions:
- Use only the retrieved documentation context below.
- Do not use outside knowledge.
- End each factual sentence with one or more inline citations in this exact format: [filename, chunk_id]
- If the answer is not supported by the context, say: I could not find that in the local documentation.

Retrieved context:
{context}

User question:
{query}
"""

    except Exception as e:
        print(f"RAG ERROR: {e}", file=sys.stderr, flush=True)
        return f"RAG error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=8001)
