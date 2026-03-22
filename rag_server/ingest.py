import os
import shutil
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import CHROMA_DB_PATH, EMBEDDING_MODEL


DOCS_DIR = "docs_source"
COLLECTION_NAME = "nexcode_docs"


def load_documents() -> list[Document]:
    documents = []

    for root, _, files in os.walk(DOCS_DIR):
        for filename in files:
            filepath = os.path.join(root, filename)

            if not filename.lower().endswith((".txt", ".md", ".py", ".json")):
                continue

            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().strip()

            if not text:
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": filepath.replace("\\", "/"),
                        "filename": filename,
                    },
                )
            )

    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        add_start_index=True,
    )

    chunks = splitter.split_documents(documents)

    for i, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_id"] = i

    return chunks


def build_vectorstore(chunks: list[Document]):
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    if os.path.exists(CHROMA_DB_PATH):
        shutil.rmtree(CHROMA_DB_PATH)

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH,
        collection_name=COLLECTION_NAME,
    )


if __name__ == "__main__":
    print("Loading documents...")
    docs = load_documents()
    print(f"Loaded {len(docs)} documents")

    print("Splitting documents...")
    chunks = split_documents(docs)
    print(f"Created {len(chunks)} chunks")

    print("Building Chroma vector store...")
    build_vectorstore(chunks)

    print("Done. Vector DB built successfully.")
