from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from config.settings import GROQ_API_KEY


def get_llm(provider: str, model: str):
    """
    Returns the appropriate LangChain chat model based on provider choice.
    Supports: groq, ollama, openai, anthropic
    """
    if provider == "groq":
        return ChatGroq(
            model=model,
            api_key=GROQ_API_KEY,
            streaming=True,
            temperature=0.2,
        )
    elif provider == "ollama":
        return ChatOllama(
            model=model,
            temperature=0.2,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, streaming=True, temperature=0.2)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, streaming=True, temperature=0.2)
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose from: groq, ollama, openai, anthropic")
