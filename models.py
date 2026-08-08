# models.py
# -----------------------------------------------------------------------------
# "Models" here means the SHAPE of the data going in and out of our API.
# We use Pydantic (built into FastAPI). Pydantic checks incoming JSON for us:
# if the frontend sends the wrong type or a missing field, FastAPI returns a
# clear error automatically instead of crashing deep inside our code.
# -----------------------------------------------------------------------------

from pydantic import BaseModel, EmailStr, Field


# ---- What the frontend SENDS when a new user signs up -----------------------
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1)          # ... means "required"
    email: EmailStr                               # EmailStr rejects invalid emails
    password: str = Field(..., min_length=6)      # force at least 6 characters


# ---- What the frontend SENDS when logging in --------------------------------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---- What we SEND BACK after a successful signup/login ----------------------
class TokenResponse(BaseModel):
    access_token: str      # the JWT the frontend stores and sends on each request
    token_type: str = "bearer"
    name: str              # the user's name, handy for showing "Hi, <name>"


# ---- One message in a chat conversation -------------------------------------
# role is either "user" (the student) or "assistant" (the AI's previous reply).
class ChatMessage(BaseModel):
    role: str
    content: str


# ---- What the frontend SENDS when asking a question -------------------------
class ChatRequest(BaseModel):
    question: str
    # The recent conversation so the AI can understand follow-up questions like
    # "explain that more". The frontend keeps this list and sends it each time.
    history: list[ChatMessage] = []


# ---- What we SEND BACK after answering --------------------------------------
class ChatResponse(BaseModel):
    answer: str
    # "sources" are short snippets from the PDF that the answer was based on,
    # so the student can trust and verify where the information came from.
    sources: list[str] = []
