# main.py
# -----------------------------------------------------------------------------
# This is the ENTRY POINT of the whole backend. You start the app by running,
# from inside the Parho folder:
#
#     uvicorn main:app --reload
#
# "main:app" means: in the file main.py, use the variable called `app`.
# --reload restarts the server automatically when you edit a file (handy while
# learning). Then open http://127.0.0.1:8000 in your browser.
#
# This file's job is small: create the app, allow the browser to talk to it
# (CORS), plug in the route groups, and serve the frontend files.
# -----------------------------------------------------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings

# Import the three route groups we built.
import auth_routes
import pdf_routes
import chat_routes

# Create the FastAPI application object.
app = FastAPI(title="Parho - RAG Study App")

# --- CORS -------------------------------------------------------------------
# CORS controls which websites' JavaScript may call this API. When the frontend
# is served from the SAME server (local dev) this is just a formality. But once
# the frontend lives elsewhere (e.g. Vercel), the browser BLOCKS its calls unless
# the backend says that origin is allowed. We read the allowed list from settings
# (env var ALLOWED_ORIGINS); it defaults to "*" (any site) for an easy first
# deploy, and you can lock it to your Vercel URL later without changing code.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes -----------------------------------------------------------------
# include_router adds all the endpoints from each file (with their /auth, /pdf,
# /chat prefixes). Now the app knows about /auth/signup, /pdf/upload, etc.
app.include_router(auth_routes.router)
app.include_router(pdf_routes.router)
app.include_router(chat_routes.router)


@app.get("/health")
def health():
    """A tiny endpoint to confirm the server is alive. Visit /health to test."""
    return {"status": "ok", "app": "Parho"}


# --- Frontend ---------------------------------------------------------------
# We serve the plain HTML/CSS/JS in the "static" folder. Visiting the root URL
# ("/") returns index.html so the app opens straight away.
STATIC_DIR = settings.UPLOAD_DIR.parent / "static"


@app.get("/")
def home():
    """Serve the main page (the login/chat screen)."""
    return FileResponse(str(STATIC_DIR / "index.html"))


# Mount the rest of the static files (style.css, script.js) under /static so the
# HTML can load them with <link href="/static/style.css"> etc.
# This line goes LAST so it doesn't accidentally swallow the API routes above.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
