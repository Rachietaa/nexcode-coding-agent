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


def load_vectorstore() -> Chroma:
    """Load the persisted ChromaDB vector store."""
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embeddings,
        collection_name="nexcode_docs",
    )


def hyde_retrieve(query: str) -> list[str]:
    """
    HyDE retrieval: generate a hypothetical answer first, then use it for retrieval.
    Falls back to direct query retrieval if LLM is unavailable.
    """
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": RAG_TOP_K})

    try:
        # Step 1: Generate a hypothetical answer using a fast LLM
        llm = ChatGroq(model="llama-3.1-8b-instant", api_key=GROQ_API_KEY, temperature=0)
        hyde_prompt = (
            f"Write a short technical documentation snippet or code example that directly answers: '{query}'. "
            f"Be concise and specific."
        )
        hypothetical_doc = llm.invoke(hyde_prompt).content

        # Step 2: Retrieve using the hypothetical doc (not the raw query)
        docs = retriever.invoke(hypothetical_doc)

    except Exception:
        # Fallback: direct query retrieval
        docs = retriever.invoke(query)

    return [doc.page_content for doc in docs]
