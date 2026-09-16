<!-- Guidance for AI coding agents working on RagTube -->
# RagTube — Copilot Instructions

- RagTube is a FastAPI + React/Vite RAG system for asking questions about YouTube videos.
- Production providers are Groq for generation and Hugging Face for embeddings. Do not add Ollama as a remote deployment requirement.
- Core flow: `backend/app/routes/ingest.py` fetches captions, chunks them, and persists FAISS under `VECTORSTORE_DIR`; `backend/app/routes/query.py` retrieves chunks and streams NDJSON from `backend/app/services/llm.py`.
- Backend entrypoint: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
- Render uses the repository root as Docker context and `backend/Dockerfile` as its Dockerfile. Render supplies `PORT`.
- Frontend deployment uses Cloudflare Pages with root directory `frontend`, build command `npm run build`, and output directory `dist`.
- Set frontend `VITE_API_BASE` to the Render backend URL in Cloudflare Pages. Local development falls back to `http://127.0.0.1:8000`.
- Set backend `CORS_ORIGINS` to the Cloudflare Pages origin plus localhost origins when needed. Never use `*` for the production frontend.
- Required provider variables are `GROQ_API_KEY`, `HF_API_TOKEN`, `LLM_PROVIDER=groq`, `EMBED_PROVIDER=hf`, `GROQ_MODEL`, and `HF_EMBED_MODEL`.
- Never commit `.env` files or credentials. Use `.env.example` for documented variable names only.
- `fetch_transcript_data` returns structured error data for unavailable/private/blocked videos. Preserve that behavior when changing ingestion.
- `chunk_text` uses character counts with timestamped segment metadata when captions are available.
- FAISS storage on Render Free is ephemeral; users may need to ingest a video again after restart or redeploy.
- Router files define empty-path endpoints and are mounted with prefixes in `backend/app/main.py`.
- Validate backend changes with the repository virtualenv and frontend changes with `npm run build` from `frontend/`.
