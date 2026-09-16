# RagTube

RagTube is a Retrieval-Augmented Generation app for asking questions about YouTube videos. The React + Vite frontend sends a YouTube URL to a FastAPI backend. The backend fetches captions with `yt-dlp`, chunks the transcript, creates Hugging Face embeddings, stores them in FAISS, retrieves relevant chunks, and streams an answer from Groq.

## Current architecture

```text
React + Vite
    |
    | HTTPS / JSON + NDJSON streaming
    v
FastAPI
    |-- YouTube captions via yt-dlp
    |-- Hugging Face embeddings
    |-- FAISS vector store
    `-- Groq chat completions
```

Ollama is not required by the current application or its deployment configuration.

## Run locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example backend/.env
```

Edit `backend/.env` and set `GROQ_API_KEY` and `HF_API_TOKEN`. The default local CORS origins and vectorstore path are already suitable for development.

Start the backend from the repository root:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, paste a public YouTube URL, ingest it, and ask a question. The frontend uses `VITE_API_BASE` when set and otherwise falls back to `http://127.0.0.1:8000` for local development.

## API

- `GET /` — basic service response
- `GET /health` — safe health/configuration status
- `GET /docs` — FastAPI Swagger UI
- `GET /diagnostics` — outbound Hugging Face DNS/HTTP diagnostics
- `GET /ingest?video_url=...` — fetch captions and build FAISS files
- `GET /query?question=...&provider=groq&video_id=...` — stream NDJSON answer chunks

Example:

```bash
curl "http://127.0.0.1:8000/ingest?video_url=https://www.youtube.com/watch?v=VIDEO_ID"
curl -N "http://127.0.0.1:8000/query?question=What%20is%20the%20main%20point%3F&provider=groq"
```

## Configuration

Use `.env.example` as the safe reference. Required production credentials are supplied through the hosting provider, never committed to the repository:

- `GROQ_API_KEY` — required when `LLM_PROVIDER=groq`
- `HF_API_TOKEN` — required when `EMBED_PROVIDER=hf`
- `LLM_PROVIDER=groq`
- `GROQ_MODEL=llama-3.1-8b-instant`
- `EMBED_PROVIDER=hf`
- `HF_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2`
- `VECTORSTORE_DIR` — writable FAISS directory
- `CORS_ORIGINS` — comma-separated allowed frontend origins

## Free public deployment

See [DEPLOY.md](DEPLOY.md) for the exact ₹0 target setup: React on Cloudflare Pages Free and FastAPI in a Render Free Web Service. The `space/` directory is an optional legacy Streamlit experiment; it is not the primary application or deployment path.

## Storage limitation

FAISS files are stored locally under `VECTORSTORE_DIR`. Render's free filesystem is ephemeral, so an instance restart or redeploy can remove the index. Re-ingest a YouTube video to rebuild it. No paid or external vector database is required.

## Project structure

```text
backend/app/main.py                 FastAPI app and CORS
backend/app/config.py               Environment configuration
backend/app/routes/ingest.py        Transcript ingestion
backend/app/routes/query.py         Retrieval and streamed answers
backend/app/services/transcript.py  YouTube caption parsing/chunking
backend/app/services/embeddings.py  Hugging Face embeddings
backend/app/services/retriever.py   FAISS persistence/search
backend/app/services/llm.py         Groq/Hugging Face generation
frontend/src/                       React + Vite application
backend/Dockerfile                  Render deployment image
```
