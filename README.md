# Parho — a RAG study web app

Upload your PDF notes, then ask questions about them. Parho finds the relevant
parts of your PDF and uses an AI model to answer, remembering the conversation
so follow-up questions work.

- **Backend:** FastAPI
- **Answers:** ChatGroq (Llama)
- **Embeddings:** Google `gemini-embedding-001` by default (local HuggingFace optional)
- **Vector store:** Chroma (saved to disk)
- **Login/signup:** MongoDB + JWT tokens
- **Limit:** 2 PDF uploads per user per day
- **Frontend:** plain HTML + CSS + vanilla JS

---

## 1. What you need first

1. **Python 3.10+** (you already have this).
2. **MongoDB running** on your machine. Easiest option: install *MongoDB
   Community Server* and it runs at `mongodb://localhost:27017` by default.
   (Or use a free MongoDB Atlas cloud database and paste its connection string
   into `.env`.)
3. **API keys** for Groq and Google — you already have these in your
   `D:\Langchain Models\.env` file, and Parho reads that file automatically.

---

## 2. Setup (one time)

Open a terminal **inside the `Parho` folder** and, with your venv active:

```bash
pip install -r requirements.txt
```

Then create your secret key for logins. Copy `.env.example` to `.env` and set a
`SECRET_KEY` (generate one with the command below), or just add `SECRET_KEY` to
your existing parent `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 3. Run it

From inside the `Parho` folder:

```bash
uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000** in your browser. Sign up, upload a PDF, and
start asking questions. The auto-generated API docs live at
**http://127.0.0.1:8000/docs**.

---

## 4. How the files fit together

Think of it in three groups: **web layer**, **AI layer (rag/)**, and **frontend**.

```
Parho/
├── main.py           # starts the app, connects all routes, serves the frontend
├── config.py         # all settings + API keys, read from .env in ONE place
├── database.py       # connects to MongoDB (users + upload records)
├── models.py         # the shape of data in/out (validated by Pydantic)
├── security.py       # password hashing + create/verify JWT login tokens
├── dependencies.py   # get_current_user: protects routes, requires a valid token
├── daily_limit.py    # the "2 PDFs per day" rule
│
├── auth_routes.py    # POST /auth/signup, POST /auth/login
├── pdf_routes.py     # POST /pdf/upload, GET /pdf/quota
├── chat_routes.py    # POST /chat
│
├── rag/              # the AI pipeline, one step per file
│   ├── doc_loader.py     # 1. load  — read text from the PDF
│   ├── text_splitter.py  # 2. split — cut text into small chunks
│   ├── embeddings.py     # 3. embed — turn chunks into number vectors (Google/HuggingFace)
│   ├── vector_store.py   # 4/5. store + retrieve chunks (Chroma), per user
│   ├── llm.py            # the ChatGroq model that writes answers
│   └── chain.py          # ties retrieval + the LLM together, with memory
│
├── static/           # the frontend
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── Dockerfile        # how Railway builds + runs the backend
├── .dockerignore     # keeps .env and junk OUT of the image
├── .gitignore        # keeps .env and junk from being pushed
├── requirements.txt
├── .env.example
└── README.md
```

### The RAG flow in one picture

**When you upload a PDF:**
`doc_loader` reads it → `text_splitter` chunks it → `embeddings` + `vector_store`
turn each chunk into numbers and save them in your private Chroma collection.

**When you ask a question:**
`chain.py` rewrites your question using the chat history → searches your Chroma
collection for the most relevant chunks → pastes them into a prompt → `llm.py`
(ChatGroq) writes the answer. If the PDF doesn't cover it, the AI falls back to
general knowledge and says so.

---

## 5. Good to know

- Each user's PDFs are kept in a **separate Chroma collection**, so users never
  see each other's documents.
- The daily limit resets at **midnight UTC** (a new day = a fresh count).
- Chroma data is saved in the `chroma_db/` folder, so your indexed PDFs survive
  a server restart. Delete that folder to wipe all stored PDFs.
- This is a learning setup. Before any real deployment you'd lock down CORS,
  use a strong `SECRET_KEY`, and serve over HTTPS.

---

## 6. Deploy: backend on Railway, frontend on Vercel (keep your keys safe)

Parho is one app in two halves: a **backend** (FastAPI — the brains: auth, PDF
processing, chat) and a **frontend** (the `static/` folder — plain HTML/CSS/JS).
We put the backend on **Railway** (it runs our Docker image) and the frontend on
**Vercel** (free, fast static hosting). They talk over the internet, so we do two
small bits of wiring.

Your secret keys are **never** put in a file you upload. You paste them into
Railway's Variables page and Railway feeds them to the app as environment
variables at runtime — `config.py` already reads them with `os.getenv`, so no
code change is needed.

> 💡 **Cost, honestly:** because embeddings are now a cloud API call (no PyTorch,
> no local model to load), the backend is light on memory — it fits small
> instances, even Render's free 512MB tier. On Railway the one-time **$5 trial
> credit** now stretches much further; for a genuinely always-on backend you'll
> still likely land on the **Hobby plan (~$5/month)**. Vercel's frontend hosting
> is free for this.

---

### Part A — Deploy the backend to Railway

**Step 1 — Prepare MongoDB Atlas.**
Your users live in MongoDB, and Railway runs in the cloud, so Atlas must accept
its connection. In Atlas: **Network Access → Add IP Address → Allow access from
anywhere (`0.0.0.0/0`)**. Your database is still protected by its username and
password; this just lets Railway reach it.

**Step 2 — Push your code to GitHub.**
Railway deploys from a GitHub repo. Create a new repo and push:
```bash
git init
git add .
git commit -m "Parho"
git remote add origin https://github.com/YOUR_NAME/parho.git
git push -u origin main
```
Because `.env` is in `.gitignore`, your keys are **not** pushed. (Double-check:
after `git add .`, run `git status` and confirm `.env` is **not** listed.)

**Step 3 — Create the Railway project.**
On <https://railway.app> click **New Project → Deploy from GitHub repo** and pick
your repo. Railway sees the `Dockerfile` and builds the backend from it. The
build is quick — just Python packages, no heavy PyTorch download anymore.

**Step 4 — Add your secrets (the safe part).**
Open your service's **Variables** tab and add:

| Name | Value |
|------|-------|
| `GROQ_API_KEY` | your Groq key (writes the answers) |
| `GOOGLE_API_KEY` | your Google key — **required**, it powers the default embeddings |
| `MONGODB_URI` | your full Atlas connection string (with user + password) |
| `SECRET_KEY` | a long random string — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |

Optionally also: `DB_NAME=parho`, `MAX_PDFS_PER_DAY=2`. You do **not** set `PORT`
— Railway sets that itself, and the Dockerfile already listens on it.

**Step 5 — Get your public URL.**
In **Settings → Networking**, click **Generate Domain**. You'll get something
like `https://parho-production.up.railway.app`. Open `THAT_URL/health` — you
should see `{"status":"ok","app":"Parho"}`. That means the backend is live.
**Copy this URL — the frontend needs it next.**

**Step 6 — Make PDFs survive restarts (recommended).**
By default Railway's disk resets on each redeploy, wiping `chroma_db/` (indexed
PDFs) and `uploads/`. Your **users are safe** (they're in Atlas), but to keep the
vector store, add a **Volume** (service → **Variables/Settings → Volumes → New
Volume**) mounted at `/home/user/app/chroma_db`. Uploaded PDFs in `uploads/` are
temporary and don't need one.

---

### Part B — Deploy the frontend to Vercel

**Step 7 — Point the frontend at your backend.**
Open `static/script.js`, find the `const API = "";` line near the top, and paste
your Railway URL (no trailing slash):
```js
const API = "https://parho-production.up.railway.app";
```
Commit and push this change to GitHub.

**Step 8 — Import the project on Vercel.**
On <https://vercel.com> click **Add New → Project** and import the same GitHub
repo. In the setup screen:
- **Framework Preset:** Other
- **Root Directory:** click **Edit** and choose **`static`** (so Vercel publishes
  only the frontend folder)
- Leave build/output settings empty — these are plain files, nothing to build.

Click **Deploy**. You'll get a URL like `https://parho.vercel.app`.

**Step 9 — Let the backend trust the frontend.**
Back in Railway's **Variables**, set `ALLOWED_ORIGINS` to your exact Vercel URL:
```
ALLOWED_ORIGINS=https://parho.vercel.app
```
Railway restarts the backend. Now open your Vercel URL, sign up, upload a PDF,
and chat. Done. 🎉

*(You can skip this step to test — CORS defaults to `*`, allowing any site — but
setting it to your real URL is the safe, correct finish.)*

---

### What gets uploaded where — and what never does

- **Both hosts pull from your GitHub repo**, and `.env` is git-ignored, so your
  keys are never uploaded to either. ✅
- **Never commit or upload** `.env` (holds your MongoDB password), `chroma_db/`,
  `uploads/`, or `__pycache__/` — all already in `.gitignore`.
- **Keys live only in Railway's Variables**, never in a file.

### Good to know
- To rotate a leaked key later, just edit the Variable in Railway — the backend
  restarts with the new value, no code change.
- Free Railway apps can sleep/limit usage; the first request after idle is slow
  while the model reloads. The Hobby plan keeps it always-on.
- Want it all on **one** host with no split (and no CORS/URL wiring)? You can
  deploy the whole Docker image (backend *and* its built-in `static/` frontend)
  to Railway alone, and skip Vercel entirely — Railway already serves the
  frontend at `/`. The split just gives the frontend a faster, free CDN.

