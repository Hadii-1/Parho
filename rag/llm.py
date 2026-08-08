# rag/llm.py
# =============================================================================
# THE LANGUAGE MODEL (LLM) THAT WRITES THE ANSWERS
# =============================================================================
# This is the "generation" part of RAG. After we retrieve the relevant PDF
# chunks, we hand them + the question to this LLM, and it writes the final
# answer in natural English.
#
# We use ChatGroq (the same provider as your Groq_test.py). Groq runs open
# models like Llama very fast. It needs your GROQ_API_KEY.
# =============================================================================

from langchain_groq import ChatGroq

from config import settings


def get_llm():
    """Create and return the ChatGroq language model.

    temperature controls creativity/randomness:
      - 0.0  = focused, consistent, factual  (best for studying)
      - 1.0+ = more creative but more likely to wander or make things up
    For a study helper we keep it low so answers stay grounded and steady."""
    return ChatGroq(
        model=settings.GROQ_MODEL,          # e.g. "llama-3.1-8b-instant"
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
    )
