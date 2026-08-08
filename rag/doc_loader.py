# rag/doc_loader.py
# =============================================================================
# STEP 1 OF THE RAG PIPELINE: LOADING
# =============================================================================
# "RAG" = Retrieval-Augmented Generation. The idea in plain words:
#   1) LOAD    the PDF text            <-- this file
#   2) SPLIT   it into small chunks
#   3) EMBED   each chunk into numbers
#   4) STORE   those numbers in a vector database (Chroma)
#   5) RETRIEVE the chunks most relevant to a question
#   6) GENERATE an answer with the LLM using those chunks
#
# This file only does STEP 1: read a PDF file and return its text as a list of
# "Document" objects. A Document is a LangChain object holding some text
# (.page_content) plus metadata like the page number (.metadata).
# =============================================================================

from langchain_community.document_loaders import PyPDFLoader


def load_pdf(file_path: str):
    """Read a PDF from disk and return a list of Document objects (one per page).

    Parameters
    ----------
    file_path : str
        The location of the PDF on disk, e.g. "uploads/mynotes.pdf".

    Returns
    -------
    list[Document]
        One Document per page. Each has:
          - page_content : the text of that page
          - metadata     : info such as {"source": "...", "page": 0}
    """
    # PyPDFLoader knows how to open a PDF and pull the text out of every page.
    # Behind the scenes it uses the "pypdf" library.
    loader = PyPDFLoader(file_path)

    # .load() actually reads the file and returns the list of Documents.
    documents = loader.load()

    # If a PDF is scanned images with no real text, this list may be empty.
    # We return it as-is; the calling code decides what to do about that.
    return documents
