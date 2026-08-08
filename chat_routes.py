# chat_routes.py
# -----------------------------------------------------------------------------
# The chat endpoint:
#   POST /chat  -> ask a question about your uploaded PDFs
#
# This is where a student's question meets the RAG chain we built in
# rag/chain.py. The route itself is thin: check login, call answer_question,
# return the result. All the AI logic lives in the rag/ files.
# -----------------------------------------------------------------------------

from fastapi import APIRouter, Depends

from dependencies import get_current_user
from models import ChatRequest, ChatResponse
from rag.chain import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])


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
    answer, sources = answer_question(
        user_id=user_id,
        question=data.question,
        history=data.history,
    )

    # Pydantic turns this into clean JSON for the frontend.
    return ChatResponse(answer=answer, sources=sources)
