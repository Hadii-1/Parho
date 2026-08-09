# chat_routes.py
# -----------------------------------------------------------------------------
# The chat endpoint:
#   POST /chat  -> ask a question about your uploaded PDFs
#
# This is where a student's question meets the RAG chain we built in
# rag/chain.py. The route itself is thin: check login, call answer_question,
# return the result. All the AI logic lives in the rag/ files.
# -----------------------------------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException
import logging

from dependencies import get_current_user
from models import ChatRequest, ChatResponse
from rag.chain import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])

# A named logger so any failure shows up clearly in the server logs (e.g. Railway).
logger = logging.getLogger("parho.chat")


@router.post("", response_model=ChatResponse)
def chat(
    data: ChatRequest,                              # {question, history} from frontend
    current_user: dict = Depends(get_current_user),  # requires a valid login token
):
    """Answer the student's question using their own PDFs (+ the chat history
    so follow-up questions make sense)."""
    user_id = str(current_user["_id"])

    # Hand everything to the RAG chain. It rewrites follow-ups, retrieves the
    # most relevant PDF chunks, and asks the LLM to write the answer.
    #
    # We wrap this so that if ANYTHING goes wrong we return a clean error instead
    # of letting the exception escape. Why this matters: an unhandled error makes
    # FastAPI send a 500 that has NO CORS headers, which the browser then blocks —
    # so the frontend can't read it and just says "Cannot reach the server". By
    # catching it and raising HTTPException, FastAPI builds a proper JSON error
    # WITH the CORS headers, so the frontend shows our message (in "detail") in
    # the chat. The full reason is written to the server logs for us to inspect.
    try:
        answer, sources = answer_question(
            user_id=user_id,
            question=data.question,
            history=data.history,
        )
    except Exception:
        logger.exception("chat failed for user %s", user_id)
        raise HTTPException(
            status_code=500,
            detail="Sorry — the assistant hit an error while answering. Please try again.",
        )

    # Pydantic turns this into clean JSON for the frontend.
    return ChatResponse(answer=answer, sources=sources)
