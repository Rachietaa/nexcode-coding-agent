import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastmcp import FastMCP
from config.settings import CHROMA_DB_PATH

mcp = FastMCP(
    name="NexCode RAG Server",
    instructions="Search local documentation using HyDE advanced RAG retrieval.",
)


@mcp.tool()
def query_documentation(query: str) -> str:
    """
    Search the local documentation vector database for relevant code examples,
    API usage, and library documentation. Uses HyDE for improved accuracy.

    Args:
        query: Natural language question about a library or API

    Returns:
        Relevant documentation chunks
    """
    if not os.path.exists(CHROMA_DB_PATH):
        return "Vector DB not found. Run: python rag_server/ingest.py first."

    try:
        from rag_server.retriever import hyde_retrieve

        chunks = hyde_retrieve(query)
        if not chunks:
            return "No relevant documentation found."

        result = f"Found {len(chunks)} relevant documentation chunks:\n\n"
        for i, chunk in enumerate(chunks, 1):
            result += f"--- Chunk {i} ---\n{chunk}\n\n"
        return result

    except Exception as e:
        return f"RAG error: {str(e)}"


if __name__ == "__main__":
    mcp.run()
