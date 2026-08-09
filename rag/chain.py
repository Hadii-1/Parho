# rag/chain.py
# =============================================================================
# THE RAG CHAIN  (this is where all the pieces come together)
# =============================================================================
# A "chain" links steps so the output of one feeds the next. Our chain answers
# a question about the user's PDFs while REMEMBERING earlier messages, so
# follow-ups like "explain that more" work.
#
# It has two prompt templates and runs three steps by hand (so you can see
# exactly what happens, and so it works on any recent LangChain version):
#
#   STEP 1  rewrite the question (history-aware)
#     A follow-up like "and why?" makes no sense to a search engine on its own.
#     So first we use the LLM + chat history to REWRITE the follow-up into a full
#     standalone question ("why does photosynthesis need light?"). We only do
#     this when there IS history; the first question is already standalone.
#
#   STEP 2  retrieve
#     We search the user's Chroma vector store with that standalone question and
#     get back the most relevant PDF chunks.
#
#   STEP 3  answer ("stuff" the chunks in)
#     We paste (a.k.a. "stuff") those chunks into the answer prompt's {context}
#     slot and ask the LLM to write the final answer.
#
#     question + history --> [1] rewrite --> [2] retrieve chunks --> [3] answer
#
# NOTE: We build these steps with the small, stable pieces from `langchain_core`
# (prompts, messages, output parser) joined by the "|" pipe operator. This style
# is called LCEL (LangChain Expression Language): `a | b` means "send a's output
# into b". So `prompt | llm | StrOutputParser()` = fill prompt, send to the
# model, then pull the plain text string out of the model's reply.
# =============================================================================

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from rag.llm import get_llm
from rag.vector_store import get_retriever


# -----------------------------------------------------------------------------
# PROMPT 1: used by PART A to rewrite a follow-up into a standalone question.
# -----------------------------------------------------------------------------
# MessagesPlaceholder("chat_history") is a slot the chain fills with the past
# messages at runtime. "{input}" is the latest user question. We tell the model
# NOT to answer here -- only to reword the question so it stands on its own.
_rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Given the chat history and the latest user question, rewrite the question "
     "so it can be understood on its own without the chat history. "
     "Do NOT answer it. If it is already standalone, return it unchanged."),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])


# -----------------------------------------------------------------------------
# PROMPT 2: used by PART B to actually write the answer.
# -----------------------------------------------------------------------------
# The "{context}" slot is where the retrieved PDF chunks get pasted in. The
# instructions below encode your chosen behaviour: use the PDF first, and only
# fall back to general knowledge if the PDF doesn't cover it -- and say so.
_answer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are Parho, a friendly study assistant. Answer the student's question "
     "clearly in English.\n\n"
     "Use the context below (taken from the student's uploaded PDF) as your main "
     "source. If the answer is in the context, base your answer on it. If the "
     "context does NOT contain the answer, you may use your own general knowledge, "
     "but clearly add a note like '(This is from general knowledge, not your PDF.)'.\n"
     "If you truly do not know, say so honestly.\n\n"
     "Context from the PDF:\n{context}"),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# -----------------------------------------------------------------------------
# HOW MUCH CONVERSATION TO REMEMBER
# -----------------------------------------------------------------------------
# "Memory" here is simple: the frontend re-sends the recent chat on every
# question, and we feed it to the model so follow-ups make sense. We cap it so
# the prompt can't grow forever (which would cost more tokens, get slower, and
# eventually overflow the model's context). 10 messages = the last ~5 exchanges
# (5 of yours + 5 of the AI's), which is plenty for follow-up questions.
MAX_HISTORY_MESSAGES = 10


def _to_lc_messages(history):
    """Convert our simple history (list of {role, content}) into the message
    objects LangChain expects. 'user' -> HumanMessage, anything else -> AIMessage.
    These fill the MessagesPlaceholder("chat_history") slots in the prompts."""
    messages = []
    for item in history:
        # `item` may be a Pydantic ChatMessage or a plain dict; support both.
        role = item.role if hasattr(item, "role") else item.get("role")
        content = item.content if hasattr(item, "content") else item.get("content")
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
    return messages


def answer_question(user_id: str, question: str, history=None):
    """The single function the API calls to get an answer.

    Runs the three RAG steps by hand and returns the answer text plus a few
    short source snippets from the PDF.

    Returns
    -------
    (answer: str, sources: list[str])
    """
    history = history or []

    # Keep only the most recent messages (see MAX_HISTORY_MESSAGES above) so the
    # "memory" we send can't grow without limit on a long conversation.
    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[-MAX_HISTORY_MESSAGES:]

    lc_history = _to_lc_messages(history)     # past messages as LangChain objects

    llm = get_llm()                           # the ChatGroq model (rag/llm.py)

    # --- STEP 1: rewrite the follow-up into a standalone question ------------
    # Only needed when there's history. `_rewrite_prompt | llm | StrOutputParser()`
    # builds a mini-chain: fill the rewrite prompt, run the model, and return the
    # model's reply as a plain string (the standalone question we'll search with).
    #
    # This is an EXTRA model call that only happens on follow-up questions. If it
    # fails for any reason (a hiccup from the model provider, a rate limit, etc.)
    # we must NOT let the whole chat break — so we catch the error and simply
    # search with the original question instead. (Before this guard, a failure
    # here is exactly what made every follow-up show "Cannot reach the server".)
    search_query = question                   # sensible default / fallback
    if lc_history:
        try:
            rewrite_chain = _rewrite_prompt | llm | StrOutputParser()
            search_query = rewrite_chain.invoke({
                "input": question,
                "chat_history": lc_history,
            })
        except Exception as exc:
            print(f"[Parho] rewrite step failed; using the original question. reason: {exc}")
            search_query = question

    # --- STEP 2: retrieve the most relevant PDF chunks ----------------------
    # retriever.invoke(text) returns a list of Document objects (the chunks whose
    # embeddings are closest to the question's embedding). If the user hasn't
    # uploaded a PDF yet, or the vector store errors, we fall back to NO context
    # so the assistant can still answer from general knowledge.
    try:
        retriever = get_retriever(user_id)    # this user's private Chroma search
        docs = retriever.invoke(search_query)
    except Exception as exc:
        print(f"[Parho] retrieval failed; answering without PDF context. reason: {exc}")
        docs = []

    # --- STEP 3: "stuff" the chunks into the answer prompt and generate ------
    # We paste all chunk texts together into one string; that string fills the
    # {context} slot of _answer_prompt. Then model writes the answer.
    context_text = "\n\n".join(doc.page_content for doc in docs)
    answer_chain = _answer_prompt | llm | StrOutputParser()
    answer = answer_chain.invoke({
        "input": question,
        "chat_history": lc_history,
        "context": context_text,
    })

    # Turn the first few chunks into short preview strings so the student can see
    # where the answer came from.
    sources = []
    for doc in docs[:3]:
        snippet = doc.page_content.strip().replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."   # keep previews short
        sources.append(snippet)

    return answer, sources

