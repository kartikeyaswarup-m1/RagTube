# RagTube

RagTube is a local Retrieval-Augmented Generation (RAG) system for asking questions about YouTube videos.  
It ingests a YouTube transcript, chunks and embeds the text, persists a FAISS vector store, and answers queries using a local or cloud LLM (Ollama or Groq).

## Quickstart

1. Create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `backend/.env` (see example below).

4. Run the backend:
```bash
uvicorn backend.app.main:app --reload
```

5. Ingest a video (replace `VIDEO_ID`):
```bash
curl "http://127.0.0.1:8000/ingest?video_url=https://www.youtube.com/watch?v=VIDEO_ID"
```

6. Query (streaming NDJSON):
```bash
curl -N "http://127.0.0.1:8000/query?question=What+is+the+main+point%3F&provider=ollama"
```

## Example `.env`
```
VECTORSTORE_DIR=./vectorstore
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3
EMBED_MODEL=nomic-embed-text
LLM_PROVIDER=ollama
GROQ_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=your_real_groq_api_key_here
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

> Important: remove any placeholder API keys from code and set `GROQ_API_KEY` in your environment if you plan to use Groq.

## How it works (high level)

- Ingest:
  - Endpoint: `GET /ingest?video_url=...`
  - Uses `yt_dlp` to fetch captions/automatic captions, parses VTT/JSON cues into timestamped segments, chunks text into ~1000-character chunks (with overlap), generates embeddings, and saves a FAISS index plus a mapping of original chunks.

- Vector store:
  - FAISS index is persisted to `VECTORSTORE_DIR/faiss.index`.
  - Original chunk objects are pickled to `VECTORSTORE_DIR/mapping.pkl`.

- Query:
  - Endpoint: `GET /query?question=...&provider=ollama|groq`
  - Retrieves nearest transcript chunks with `query_vectorstore`, builds a prompt containing only those excerpts (with timestamps), and streams LLM output as NDJSON (one JSON object per line).
  - Streamed line keys: `text` (partial output), `done` (final marker), `error` (on failure).

## Key files
- App entry: backend/app/main.py  
- Config / env: backend/app/config.py  
- Ingest route: backend/app/routes/ingest.py  
- Query route: backend/app/routes/query.py  
- Transcript parsing & chunking: backend/app/services/transcript.py  
- Embeddings: backend/app/services/embeddings.py  
- Vector store & retrieval: backend/app/services/retriever.py  
- LLM providers (Ollama / Groq): backend/app/services/llm.py

## Providers: Ollama vs Groq

- Ollama
  - Runs locally; used for embeddings and/or generation when configured.
  - Endpoints used:
    - Embeddings: `{OLLAMA_HOST}/api/embeddings`
    - Generation (streaming): `{OLLAMA_HOST}/api/generate`
  - Ensure Ollama daemon is running and required models are pulled locally.

- Groq
  - Uses the Groq cloud API via the `groq` Python SDK; requires `GROQ_API_KEY` and `GROQ_MODEL`.
  - Select provider globally via `LLM_PROVIDER` or per-request with the `provider` query parameter.

## Notes & recommendations

- After successful ingest, confirm `faiss.index` and `mapping.pkl` exist in `VECTORSTORE_DIR`.
- The code stores timestamped chunk dicts (`{"text","start","end"}`) so answers can cite timestamps.
- Consider:
  - Batching embedding requests to reduce HTTP overhead during ingest.
  - Validating embedding dimensionality before creating a FAISS index.
  - Replacing pickled mapping with a small JSON/NDJSON format for safer compatibility.
  - Removing any hard-coded or placeholder secrets from `backend/app/config.py`.

## Troubleshooting

- If `/query` reports "Vectorstore not built yet", run an ingest first.
- If embeddings fail, verify `OLLAMA_HOST`, `EMBED_MODEL`, and that Ollama is reachable.
- If Groq streaming fails, verify `GROQ_API_KEY` and that the `groq` SDK is installed.

## Next steps I can help with
- Create `backend/.env.example`.
- Implement embedding batching and dim checks in `backend/app/services/retriever.py`.
- Add a short client example to consume NDJSON streaming responses.
# RagTube

Ask questions about YouTube videos using Retrieval-Augmented Generation (RAG) powered by either local Ollama or Groq.

## Features

- **Local or Cloud LLMs** – Use Ollama locally or switch to Groq with an API key.
- **YouTube Integration** – Automatically fetch and process YouTube transcripts.
- **Vector Search** – FAISS-based semantic search for relevant content.
- **Streaming Responses** – Real-time LLM output as answers stream in.
- **Polished UI** – Modern React + Vite interface for deployment.

## Architecture

```
YouTube Video
    ↓
Transcript Fetch (yt-dlp)
    ↓
Text Chunking
    ↓
Embeddings (Ollama)
    ↓
FAISS Vector Store
    ↓
Semantic Search + LLM
    ↓
Streamed Answer
```

## Prerequisites

1. **Python 3.10+**
2. **Ollama** – Download from [ollama.ai](https://ollama.ai) for local models
3. **Groq API key** – Needed only if you want Groq-backed responses
4. **Required Models** (pull via Ollama):
   ```bash
   ollama pull llama3
   ollama pull nomic-embed-text
   ```

## Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/kartikeyaswarup-m1/ragtube.git
   cd ragtube
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables (copy `.env.example` or create `.env`):
   ```bash
   OLLAMA_HOST=http://127.0.0.1:11434
   OLLAMA_MODEL=llama3
    LLM_PROVIDER=ollama
    GROQ_API_KEY=your_groq_api_key
    GROQ_MODEL=llama-3.1-8b-instant
   EMBED_MODEL=nomic-embed-text
   VECTORSTORE_DIR=./vectorstore
   ```

## Usage

### Start Ollama

```bash
ollama serve
```

### Groq setup

If you want Groq responses, set `GROQ_API_KEY` in `backend/.env`. The query panel lets you switch between `Ollama (local)` and `Groq API` per question.

### Run Backend (FastAPI)

```bash
uvicorn backend.app.main:app --reload
```

Backend runs on `http://127.0.0.1:8000`

### Run Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

If your backend is not on the default URL, create `frontend/.env` using
`frontend/.env.example` and set `VITE_API_BASE`.

### Quick Start

1. Open the React UI in your browser
2. Paste a YouTube URL in the "Ingest a video" section
3. Click "Ingest video" to process the transcript
4. Type a question in the "Ask a question" section
5. Click "Ask" to stream the answer

## API Endpoints

### Ingest a Video
```
GET /ingest?video_url=https://youtube.com/watch?v=...
```
Returns:
```json
{
  "status": "ingested",
  "chunks": 42,
  "video_id": "dQw4w9WgXcQ"
}
```
## Paste Video Link

<img width="691" height="437" alt="Screenshot 2025-12-17 at 12 11 26 PM" src="https://github.com/user-attachments/assets/7c6d2e23-e143-47ee-a56c-6ad02c71c132" />

## Ask Questions 

<img width="691" height="451" alt="Screenshot 2025-12-17 at 12 12 56 PM" src="https://github.com/user-attachments/assets/dce0fca9-9453-4682-ab4f-ca2b08a86a8a" />

### Query
```
GET /query?question=What is the main topic?
```
Streams NDJSON response:
```
{"text": "The"}
{"text": " main"}
{"text": " topic"}
{"done": true}
```

## Project Structure

```
ragtube/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration & env loading
│   │   ├── routes/
│   │   │   ├── ingest.py        # POST /ingest endpoint
│   │   │   └── query.py         # GET /query endpoint (streaming)
│   │   └── services/
│   │       ├── transcript.py    # YouTube transcript fetching
│   │       ├── embeddings.py    # Ollama embeddings
│   │       ├── retriever.py     # FAISS vector store
│   │       └── llm.py           # LLM utilities
│   ├── vectorstore/             # Persisted FAISS index
│   └── .env                     # Environment configuration
├── frontend/
│   ├── src/                     # React app
│   ├── index.html               # Vite entry
│   ├── vite.config.js           # Vite config
│   └── package.json             # Frontend dependencies
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Configuration

Edit `backend/.env` to customize:

```bash
# Ollama connection
OLLAMA_HOST=http://127.0.0.1:11434

# Models to use
OLLAMA_MODEL=llama3              # Chat model
EMBED_MODEL=nomic-embed-text     # Embedding model

# Vector store location
VECTORSTORE_DIR=./vectorstore

# Retrieval settings
TOP_K=3                          # Number of chunks to retrieve
CHUNK_SIZE=1000                  # Characters per chunk
CHUNK_OVERLAP=200                # Character overlap between chunks

# Frontend CORS (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

## Performance Tips

- **Faster responses**: Use `phi` instead of `llama3` (much smaller model)
  ```bash
  ollama pull phi
  # Update OLLAMA_MODEL=phi in .env
  ```
- **Better quality**: Stick with `llama3` for detailed answers
- **Embedding speed**: `nomic-embed-text` is optimized for speed

## Troubleshooting

**"No transcript available"**
- Video may be age-restricted, geo-blocked, or private
- Try a different video

**"Connection refused" (Ollama)**
- Make sure Ollama is running: `ollama serve`
- Check `OLLAMA_HOST` in `.env`

**Groq API errors**
- Make sure `GROQ_API_KEY` is set in `backend/.env`
- Confirm the selected `GROQ_MODEL` is available in your Groq account

**Slow query responses**
- Switch to a faster model (`phi`)
- Reduce `TOP_K` in `.env` (fewer chunks = faster search)
- Ensure Ollama models are cached locally

**"FAISS index not found"**
- Run ingest on at least one video first
- Check `VECTORSTORE_DIR` path

## Future Enhancements

- [ ] Chunk preview & highlight
- [ ] Model selector in UI
- [ ] Caching for repeated queries
- [ ] Direct transcript upload
- [ ] Multi-user support
- [ ] Docker deployment

## License

See [LICENSE](LICENSE) file.

## Author

Created by 
[kartikeyaswarup-m1](https://github.com/kartikeyaswarup-m1)
[KAJAL-1307](https://github.com/KAJAL-1307)
