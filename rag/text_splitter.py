# rag/text_splitter.py
# =============================================================================
# STEP 2 OF THE RAG PIPELINE: SPLITTING
# =============================================================================
# Why split at all? Two reasons:
#   1) LLMs and embedding models can only read a limited amount of text at once.
#   2) Retrieval works better on SMALL, focused pieces. If a whole 30-page PDF
#      were one blob, a search for "what is photosynthesis" would return the
#      entire book. Small chunks let us fetch just the paragraph that matters.
#
# We use RecursiveCharacterTextSplitter. "Recursive" means it tries to split on
# big natural boundaries first (paragraphs), then smaller ones (sentences,
# words) until each chunk fits the target size. This keeps chunks readable
# instead of cutting mid-word.
# =============================================================================

from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(documents):
    """Take the list of page Documents and cut them into smaller chunks.

    Parameters
    ----------
    documents : list[Document]
        The output of load_pdf() from doc_loader.py.

    Returns
    -------
    list[Document]
        A longer list of smaller Documents (the "chunks").
    """
    # chunk_size    = how many CHARACTERS (roughly) each chunk should be.
    # chunk_overlap = how many characters neighbouring chunks share. Overlap
    #                 keeps sentences that fall on a boundary from losing their
    #                 context -- the end of one chunk repeats at the start of
    #                 the next, so an idea split across the cut is still whole.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )

    # split_documents keeps the metadata (page numbers etc.) on each new chunk.
    chunks = splitter.split_documents(documents)
    return chunks
