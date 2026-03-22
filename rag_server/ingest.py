"""
ONE-TIME script to build the vector database from docs_source/ files.
Run: python rag_server/ingest.py
After this runs once, never need to run again unless you add new docs.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from config.settings import CHROMA_DB_PATH, DOCS_SOURCE_PATH, EMBEDDING_MODEL
from rich.console import Console

console = Console()


def ingest_docs():
    console.print("[bold cyan]NexCode — Building Vector Database...[/bold cyan]")

    if not os.path.exists(DOCS_SOURCE_PATH):
        console.print("[red]docs_source/ folder not found.[/red]")
        return

    loader = DirectoryLoader(
        DOCS_SOURCE_PATH,
        glob="**/*",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        silent_errors=True,
    )
    documents = loader.load()

    if not documents:
        console.print("[red]No documents found in docs_source/. Add .md or .txt files first.[/red]")
        return

    console.print(f"[green]✓ Loaded {len(documents)} documents[/green]")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=64,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(documents)
    console.print(f"[green]✓ Split into {len(chunks)} chunks[/green]")

    console.print("[cyan]Loading embedding model (first time downloads ~90MB)...[/cyan]")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    console.print(f"[cyan]Storing in ChromaDB at {CHROMA_DB_PATH}...[/cyan]")
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH,
        collection_name="nexcode_docs",
    )

    console.print(f"[bold green]✓ Done! Vector DB ready at {CHROMA_DB_PATH}[/bold green]")


if __name__ == "__main__":
    ingest_docs()
