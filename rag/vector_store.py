# rag/vector_store.py
# =============================================================================
# STEP 4 & 5 OF THE RAG PIPELINE: STORE + RETRIEVE  (using Chroma)
# =============================================================================
# A "vector store" is a database built for embeddings. It stores each chunk of
# text next to its vector, and can very quickly find the chunks whose vectors
# are closest to a question's vector (i.e. the most relevant chunks).
#
# We use Chroma. It saves to a folder on disk (settings.CHROMA_DIR), so your
# indexed PDFs survive even after you restart the server.
#
# IMPORTANT DESIGN CHOICE -- one "collection" per user:
#   Every user gets their OWN named collection ("user_<id>"). This keeps each
#   student's PDFs private and separate, so User A can never retrieve chunks
#   from User B's documents.
# =============================================================================

from langchain_chroma import Chroma

from config import settings
from rag.embeddings import get_embeddings


def _collection_name(user_id: str) -> str:
    """Build a safe, per-user collection name, e.g. 'user_64f0abc...'.
    Keeping each user in a separate collection isolates their documents."""
    return f"user_{user_id}"


def get_vector_store(user_id: str) -> Chroma:
    """Open (or create) THIS user's Chroma collection.

    Passing the embedding function here matters: Chroma uses it to turn text
    into vectors both when we ADD chunks and when we SEARCH. Same model on both
    sides = comparable numbers."""
    return Chroma(
        collection_name=_collection_name(user_id),
        embedding_function=get_embeddings(),          # from embeddings.py
        persist_directory=str(settings.CHROMA_DIR),   # save to disk here
    )


def add_chunks(user_id: str, chunks) -> int:
    """Save a PDF's chunks into the user's collection.

    Called after loading + splitting a freshly uploaded PDF. Chroma embeds each
    chunk (turns it into a vector) and stores it. Returns how many chunks were
    added, just so the API can report it back to the user."""
    store = get_vector_store(user_id)
    store.add_documents(chunks)   # embeds + stores in one step
    return len(chunks)


def get_retriever(user_id: str, k: int = 4):
    """Turn the user's vector store into a "retriever".

    A retriever is the piece the chain calls to FETCH relevant chunks for a
    question. `k=4` means "give me the 4 most relevant chunks". A bigger k
    gives the LLM more context but costs more and can add noise."""
    store = get_vector_store(user_id)
    return store.as_retriever(search_kwargs={"k": k})
