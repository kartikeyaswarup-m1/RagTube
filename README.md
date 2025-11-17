# RagTube

Ask questions about YouTube videos using local Retrieval-Augmented Generation (RAG) powered by Ollama.

## Features

- **Local Processing** – No API keys needed. Everything runs on your machine.
- **YouTube Integration** – Automatically fetch and process YouTube transcripts.
- **Vector Search** – FAISS-based semantic search for relevant content.
- **Streaming Responses** – Real-time LLM output as answers stream in.
- **Chat History** – Previous queries stored in sidebar for quick reference.
- **Minimalist UI** – Clean, dark-themed interface with Streamlit.

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
2. **Ollama** – Download from [ollama.ai](https://ollama.ai)
3. **Required Models** (pull via Ollama):
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
   EMBED_MODEL=nomic-embed-text
   VECTORSTORE_DIR=./vectorstore
   ```

## Usage

### Start Ollama

```bash
ollama serve
```

### Run Backend (FastAPI)

```bash
uvicorn backend.app.main:app --reload
```

Backend runs on `http://127.0.0.1:8000`

### Run Frontend (Streamlit)

```bash
streamlit run frontend/streamlit_app.py
```

Frontend runs on `http://localhost:8501`

### Quick Start

1. Open Streamlit UI in browser
2. Paste a YouTube URL in the "Load Video" section
3. Click "Load" to ingest and process the video
4. Type a question in the "Question" field
5. Click "Send" to stream the answer

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
│   └── streamlit_app.py         # Streamlit UI
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

Created by [kartikeyaswarup-m1](https://github.com/kartikeyaswarup-m1)
