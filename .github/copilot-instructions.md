<!-- Guidance for AI coding agents working on RagTube -->
# RagTube — Copilot Instructions

Quick, project-specific guidance so an AI coding agent can be immediately productive.

1) Big picture
- RagTube is a local Retrieval-Augmented Generation (RAG) system for asking questions about YouTube videos.
- Core pipeline: ingest a YouTube transcript → chunk_text → generate embeddings (via Ollama) → persist to FAISS → retrieve & answer via local LLM (Ollama).

2) Where to look (quick links)
- App entry: `backend/app/main.py` (FastAPI; routers are mounted here).
- Ingest flow: `backend/app/routes/ingest.py` → calls `backend/app/services/transcript.py` and `backend/app/services/retriever.py`.
- Query flow: `backend/app/routes/query.py` → calls `backend/app/services/retriever.py` and uses `ollama.chat` to produce answers.
- Transcript helpers: `backend/app/services/transcript.py` (`fetch_transcript`, `chunk_text`).
- Embeddings: `backend/app/services/embeddings.py` (HTTP POST to Ollama `/api/embeddings`).
- Vectorstore: `backend/app/services/retriever.py` (FAISS index and `mapping.pkl` persisted under `VECTORSTORE_DIR`).
- Config/env: `backend/app/config.py` (loads `backend/.env`, creates `VECTORSTORE_DIR`).

3) Runtime & setup notes
- Run backend (from repo root):
  `uvicorn backend.app.main:app --reload`
- Ollama must be installed and running locally. Pull required models before use, for example:
  `ollama pull phi3`
  `ollama pull nomic-embed-text`
- Check `backend/.env` for these critical variables (examples in `README.md`):
  - `VECTORSTORE_DIR` (where `faiss.index` and `mapping.pkl` are stored)
  - `OLLAMA_HOST` (default `http://127.0.0.1:11434`)
  - `OLLAMA_MODEL`, `EMBED_MODEL`

4) Project-specific conventions & pitfalls
- Router files use empty-path endpoints and are mounted with prefixes in `main.py`. When adding a new router, always `include_router` in `main.py`.
- `fetch_transcript` returns string error messages (e.g. "No transcript available...") rather than always raising. Ingest code checks returned text for error strings — preserve this behavior or update both caller and callee.
- `chunk_text` uses character counts (default `chunk_size=1000`, `overlap=200`) as an approximation for tokens; keep sizes consistent across changes.
- `embeddings.get_embedding` POSTs to `OLLAMA_HOST/api/embeddings` and expects a JSON response with an `embedding` field — errors are raised as `RuntimeError`.
- `retriever.save_vectorstore` writes `faiss.index` and `mapping.pkl` to `VECTORSTORE_DIR`. `query_vectorstore` will raise `RuntimeError` if these files don't exist — ingest must be run first.

5) Integration points to be mindful of
- Ollama embedding endpoint: `backend/app/services/embeddings.py` (HTTP). If switching to an external embedding service, adapt both `save_vectorstore` and `query_vectorstore` call sites.
- The LLM call in `backend/app/routes/query.py` uses the Python `ollama` client (`ollama.chat`) and composes a prompt by joining the retrieved contexts. Keep prompt-building changes minimal and test locally with models pulled to Ollama.

6) Examples / change recipes
- Add a new API route:
  - Create `backend/app/routes/myroute.py` with `APIRouter()` and endpoints defined at `""` (no prefix inside the file).
  - Add `app.include_router(myroute.router, prefix="/myroute", tags=["myroute"])` in `backend/app/main.py`.

- Add a new service using embeddings:
  - Put helper in `backend/app/services/` and call `get_embedding(text)` from `embeddings.py`.
  - Persist vectors under `VECTORSTORE_DIR` (config ensures the directory exists).

7) Tests & debugging
- There are no automated tests in the repo. For quick validation:
  - Start Ollama and pull models.
  - Run the backend and use Swagger UI at `http://127.0.0.1:8000/docs` to call `/ingest` and `/query`.
  - Check `VECTORSTORE_DIR` for `faiss.index` and `mapping.pkl` after successful ingest.

8) Coding style & small rules
- Python 3.10+ type hints are used (e.g. `list[str]`). Keep compatibility with Python 3.10+.
- Avoid moving the `.env` load logic; `backend/app/config.py` expects `backend/.env` relative to `BASE_DIR`.

9) When unsure, check these files first
- `backend/app/routes/ingest.py`
- `backend/app/routes/query.py`
- `backend/app/services/transcript.py`
- `backend/app/services/embeddings.py`
- `backend/app/services/retriever.py`

If anything here is unclear or you want more detail (examples of prompts, exact env values, or where to add tests), tell me which section to expand and I will iterate.