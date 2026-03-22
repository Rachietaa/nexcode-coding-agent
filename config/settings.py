import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

DEFAULT_PROVIDER = "groq"
DEFAULT_MODEL = "llama-3.3-70b-versatile"

CHROMA_DB_PATH = "./chroma_db"
DOCS_SOURCE_PATH = "./docs_source"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
RAG_TOP_K = 5
