"""
Advanced RAG retriever using HyDE (Hypothetical Document Embeddings).

HyDE technique:
  Instead of embedding the raw user query, we first ask the LLM to generate
  a hypothetical answer/code snippet. We then embed THAT hypothetical document.
  This bridges the semantic gap between short queries and long documentation chunks,
  dramatically improving retrieval accuracy for technical/code queries.
"""
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

from config.settings import CHROMA_DB_PATH, EMBEDDING_MODEL, GROQ_API_KEY, RAG_TOP_K

COLLECTION_NAME = "nexcode_docs"


def load_vectorstore() -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )


def generate_hypothetical_doc(query: str) -> str:
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        temperature=0,
        timeout=15,
        max_retries=0,
    )

    prompt = f"""
Rewrite the user query into a short technical documentation paragraph for semantic retrieval.

User query:
{query}

Rules:
- One paragraph only.
- Under 80 words.
- No bullets, no markdown, no code, no citations.
- Use terminology likely to appear in official documentation.
- Directly describe the relevant concepts, APIs, and behavior.
"""

    response = llm.invoke(prompt)
    content = response.content.strip()
    return content if content else query


def hyde_retrieve_with_citations(query: str) -> list[dict]:
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": RAG_TOP_K})

    try:
        rewritten_query = generate_hypothetical_doc(query)
    except Exception:
        rewritten_query = query

    docs_from_query = retriever.invoke(query)
    docs_from_hyde = retriever.invoke(rewritten_query)

    seen = set()
    merged_docs = []

    for doc in docs_from_query + docs_from_hyde:
        source = doc.metadata.get("source", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "unknown")
        key = (source, chunk_id)

        if key not in seen:
            seen.add(key)
            merged_docs.append(doc)

    results = []
    for i, doc in enumerate(merged_docs[:RAG_TOP_K], start=1):
        results.append({
            "rank": i,
            "source": doc.metadata.get("source", "unknown"),
            "filename": doc.metadata.get(
                "filename", doc.metadata.get("source", "unknown")
            ),
            "chunk_id": doc.metadata.get("chunk_id", i),
            "content": doc.page_content.strip(),
        })

    return results


def format_citation_context(results: list[dict]) -> str:
    blocks = []
    for item in results:
        filename = item.get("filename", "unknown")
        chunk_id = item.get("chunk_id", "unknown")
        content = item.get("content", "").strip()
        blocks.append(f"[Source: {filename} | Chunk: {chunk_id}]\n{content}")
    return "\n\n".join(blocks)
