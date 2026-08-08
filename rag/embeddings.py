# rag/embeddings.py
# =============================================================================
# STEP 3 OF THE RAG PIPELINE: EMBEDDINGS
# =============================================================================
# An "embedding" is a list of numbers (a vector) that represents the MEANING of
# a piece of text. Texts with similar meaning get similar vectors. This is the
# magic that lets us search by meaning instead of exact keywords: the question
# "how do plants make food?" can match a chunk that says "photosynthesis",
# even though they share no words.
#
# This app can use EITHER of two embedding providers, chosen in .env with
# the EMBEDDING_PROVIDER setting:
#
#   "huggingface" (default) -> runs a small model on YOUR OWN machine
#       (sentence-transformers/all-MiniLM-L6-v2). No API key needed, works
#       offline, and never breaks when a cloud provider renames its models.
#       The model downloads once (~90MB) the first time, then is cached locally.
#
#   "google" -> uses Google's cloud embeddings (needs GOOGLE_API_KEY). Fast and
#       nothing to download, but Google changes model names over time; if you
#       see a 404 "model not found", update EMBEDDING_MODEL in .env.
#
# WHICHEVER you choose, the SAME model must be used both to STORE chunks and to
# SEARCH, or the vectors aren't comparable. We build the object ONCE (lazily, on
# first use) and reuse it. IMPORTANT: if you switch providers later, delete the
# chroma_db folder first, because different models make different-length vectors
# and mixing them corrupts the search.
# =============================================================================

from config import settings

# We cache the one shared embeddings object here after building it. Starts as
# None and is filled in on the first call to get_embeddings().
_embeddings = None


def get_embeddings():
    """Return the shared embeddings object, building it on first use.

    Both the vector store (when saving PDF chunks) and the retriever (when
    searching for a question) call this, so they always use the SAME model.
    We import the provider's library INSIDE the branch so you only need the
    package for the provider you actually chose."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings

    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "google":
        # Cloud embeddings from Google GenAI. Needs GOOGLE_API_KEY in .env.
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        _embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL,          # e.g. models/text-embedding-004
            google_api_key=settings.GOOGLE_API_KEY,
        )
    else:
        # Default: local HuggingFace embeddings (same as your earlier script).
        # model_name is the sentence-transformers model to run on your machine.
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(model_name=settings.HF_EMBEDDING_MODEL)

    return _embeddings
