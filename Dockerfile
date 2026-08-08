# Dockerfile  —  how Railway builds and runs the Parho backend
# =============================================================================
# Railway (and most container hosts) can run any web app if you give it a
# Dockerfile. The host builds this image, starts it, and sends web traffic to
# the port named by the $PORT environment variable (Railway sets this for you).
# So the only hard rules are: install our deps, copy our code, and at the end run
# the server listening on 0.0.0.0:$PORT.
#
# Your SECRET KEYS are NOT in this file and must NOT be. They are added later in
# Railway's "Variables" page, and the host injects them as environment variables
# at runtime. config.py already reads them with os.getenv, so nothing else needs
# to change.
# =============================================================================

FROM python:3.11-slim

# Build tools — some AI packages (chromadb, tokenizers) may compile on install.
# Installing these first avoids a surprise "compiler not found" build failure.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

# HF best practice: run as a normal (non-root) user with id 1000, not root.
RUN useradd -m -u 1000 user
USER user

# Env for that user. PATH includes ~/.local/bin where pip puts console scripts.
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

# All our code lives here, owned by the "user" account so the app can write to
# it (Chroma's chroma_db/ and the temporary uploads/ folder live under here).
WORKDIR /home/user/app

# Use Google cloud embeddings by default — an API call, so there's NO local
# model to download. That keeps this image small and makes it start fast (and
# fit comfortably in small free-tier RAM). Override with a Railway variable only
# if you ever switch back to a local model.
ENV EMBEDDING_PROVIDER=google

# 1) Install Python dependencies first (copied alone so Docker can cache this
#    layer and skip re-installing every time you change app code).
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 2) Copy the rest of the app in.
COPY --chown=user . .

# (No embedding model to pre-download — Google embeddings are a cloud API call.
#  If you ever switch back to a local model, re-add a pre-download step here so
#  the first PDF upload isn't slow.)

# The hosting platform tells us which port to listen on through the $PORT
# environment variable. Railway sets this automatically (and it changes between
# deploys), so we must NOT hard-code a port. If $PORT isn't set (e.g. you run the
# image on your own machine), we fall back to 7860. EXPOSE is just documentation.
EXPOSE 7860

# Start the FastAPI server. NOTE: no --reload in production, and host 0.0.0.0 so
# it's reachable from outside the container. We use the *shell* form of CMD (no
# JSON [] brackets) on purpose — the shell is what expands ${PORT} at runtime.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}
