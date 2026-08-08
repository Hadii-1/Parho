# pdf_routes.py
# -----------------------------------------------------------------------------
# Endpoints for working with PDFs:
#   GET  /pdf/quota   -> how many uploads the user has left today
#   POST /pdf/upload  -> upload a PDF; we load, split, embed and store it
#
# Both are PROTECTED: the `current_user = Depends(get_current_user)` argument
# means FastAPI requires a valid login token before the code runs. `current_user`
# is the user document returned by that dependency (see dependencies.py).
# -----------------------------------------------------------------------------

from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status

from config import settings
from dependencies import get_current_user
from daily_limit import can_upload, record_upload, remaining_today
from rag.doc_loader import load_pdf
from rag.text_splitter import split_documents
from rag.vector_store import add_chunks

router = APIRouter(prefix="/pdf", tags=["pdf"])


@router.get("/quota")
def get_quota(current_user: dict = Depends(get_current_user)):
    """Tell the frontend how many uploads remain today, so it can show it."""
    user_id = str(current_user["_id"])
    return {
        "remaining": remaining_today(user_id),
        "max_per_day": settings.MAX_PDFS_PER_DAY,
    }


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),               # the uploaded file from the form
    current_user: dict = Depends(get_current_user),
):
    """Accept a PDF, run it through the RAG pipeline, and store its chunks.

    Order of checks matters: we verify the file type and the daily limit BEFORE
    doing any expensive work."""
    user_id = str(current_user["_id"])

    # 1) Only accept PDFs. Reject anything else early with a clear message.
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    # 2) Enforce the "2 PDFs per day" rule before spending time/API calls.
    if not can_upload(user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,  # 429 = too many requests
            detail=f"Daily limit reached. You can upload {settings.MAX_PDFS_PER_DAY} "
                   f"PDFs per day. Please try again tomorrow.",
        )

    # 3) Save the uploaded file to disk so PyPDFLoader can open it by path.
    #    We prefix with the user id to avoid two users' files clashing.
    safe_name = Path(file.filename).name        # strip any folder parts for safety
    saved_path = settings.UPLOAD_DIR / f"{user_id}__{safe_name}"
    with open(saved_path, "wb") as f:
        f.write(await file.read())              # read the upload and write it out

    try:
        # 4) THE RAG INGESTION PIPELINE (steps 1->4 from the rag/ files):
        documents = load_pdf(str(saved_path))   # load  -> pages of text
        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not read any text from this PDF (is it a scanned image?).",
            )
        chunks = split_documents(documents)      # split -> small chunks
        added = add_chunks(user_id, chunks)      # embed + store in Chroma
    finally:
        # 5) We no longer need the raw PDF once its text is stored, so delete it
        #    to keep the disk clean. `finally` runs whether or not step 4 failed.
        if saved_path.exists():
            saved_path.unlink()

    # 6) Only now (success) do we count this against the daily limit.
    record_upload(user_id, safe_name)

    return {
        "message": f"'{safe_name}' processed successfully. You can now ask questions about it.",
        "chunks_added": added,
        "remaining_today": remaining_today(user_id),
    }
