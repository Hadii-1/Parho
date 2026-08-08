# config.py
# -----------------------------------------------------------------------------
# This file collects ALL the settings for the app in ONE place.
# Instead of scattering API keys and options across many files, we read them
# here once and import "settings" wherever we need them.
#
# The values come from a ".env" file (a plain text file of KEY=VALUE lines).
# We never hard-code secret keys in the code, because code often gets shared
# or pushed to GitHub, and leaking keys is dangerous.
# -----------------------------------------------------------------------------

import os
from pathlib import Path
from dotenv import load_dotenv  # small library that reads the .env file for us

# Path(__file__) is THIS file. .resolve().parent is the folder it lives in (Parho/).
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from two possible places:
# 1) A ".env" inside the Parho folder (if you make one just for this app).
# 2) The ".env" one folder up (D:\Langchain Models\.env) where your existing
#    GROQ_API_KEY and GOOGLE_API_KEY already live.
# override=False means: if a variable is already set, don't overwrite it.
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env", override=False)


class Settings:
    """A simple container class. We create one instance (called `settings`)
    at the bottom, then do `from config import settings` in other files."""

    # --- API keys (read from the environment) -------------------------------
    # These must exist in your .env file. If they are missing the AI calls fail.
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # --- Model names --------------------------------------------------------
    # The Groq chat model that WRITES the answers. Matches your Groq_test.py.
    # You can change this to any model Groq supports.
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Which embedding provider to use: "google" (cloud API, default) or
    # "huggingface" (local model). See rag/embeddings.py for the trade-offs.
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "google")

    # The local HuggingFace model (used when EMBEDDING_PROVIDER = "huggingface").
    # Small and fast, runs on your machine. Downloads once (~90MB) then is cached.
    HF_EMBEDDING_MODEL: str = os.getenv(
        "HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )

    # The Google model (used when EMBEDDING_PROVIDER = "google"). Turns text into
    # "embeddings" (lists of numbers). gemini-embedding-001 is the current GA
    # model (3072 dimensions). Google renames these over time; if you get a
    # 404 "model not found", set EMBEDDING_MODEL in .env to a current name.
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

    # --- Database -----------------------------------------------------------
    # Where MongoDB is running. The default is a local MongoDB on your machine.
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DB_NAME: str = os.getenv("DB_NAME", "parho")

    # --- Security (JWT login tokens) ----------------------------------------
    # SECRET_KEY signs the login tokens. Anyone with this key can forge logins,
    # so keep it secret and use a long random value in real projects.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-to-a-long-random-string")
    JWT_ALGORITHM: str = "HS256"          # the maths used to sign the token
    TOKEN_EXPIRE_MINUTES: int = 60 * 24   # a login stays valid for 24 hours

    # --- App rules ----------------------------------------------------------
    MAX_PDFS_PER_DAY: int = int(os.getenv("MAX_PDFS_PER_DAY", "2"))  # your 2/day rule

    # --- CORS (which websites may call this API from a browser) -------------
    # Once the frontend is hosted separately (e.g. on Vercel), the browser will
    # BLOCK its calls to this backend unless we allow that website's address.
    # This is a comma-separated list. The default "*" means "allow any site",
    # which is convenient for first setup. Later, lock it down by setting, e.g.:
    #   ALLOWED_ORIGINS=https://parho.vercel.app
    ALLOWED_ORIGINS: list = [
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
    ]

    # --- Folders (created automatically at startup) -------------------------
    UPLOAD_DIR: Path = BASE_DIR / "uploads"      # temporary place for uploaded PDFs
    CHROMA_DIR: Path = BASE_DIR / "chroma_db"    # where the vector store saves data


# Create ONE shared settings object that the rest of the app imports.
settings = Settings()

# Make sure the folders exist so we never crash trying to write into them.
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.CHROMA_DIR.mkdir(exist_ok=True)
