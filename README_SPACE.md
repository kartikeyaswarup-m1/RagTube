Hugging Face Space: Quick README and Conversion Notes

Goal

- Run RagTube as a single Hugging Face Space (Streamlit or Gradio) so the whole app (ingest + retrieve + answer) runs inside the Space.
- Use Hugging Face Inference API for embeddings (or HF-hosted models) and an external LLM provider (Groq) via API keys stored as Space secrets.

High-level choices

- Option A (recommended): Use `Streamlit` Space and set `frontend/streamlit_app.py` as the entrypoint. Convert backend calls to in-process function calls (no FastAPI).
- Option B: Use `Gradio` Space and port UI to Gradio. Same in-process approach.

Tradeoffs / notes

- Spaces are free but have resource limits. Heavy CPU/GPU usage (large embeddings, FAISS with large indexes) may be slow or unsupported.
- Persistent disk in Spaces is ephemeral for free tier. If you need persistent vectorstore across deploys/restarts, use remote storage (S3/Hugging Face Hub) or re-ingest on startup.
- Avoid compiling heavy native libs (faiss-cpu) in the Space build step if possible. Use a lightweight in-memory similarity (numpy / sklearn) for small demos.

Required Secrets (set in the Space settings)

- `HF_API_TOKEN` — Hugging Face token for the Inference/Embeddings API (if using HF inference).
- `GROQ_API_KEY` — Groq key (if you keep Groq as your LLM provider).
- `EMBED_MODEL` — optional (e.g. `sentence-transformers/all-MiniLM-L6-v2` or HF embed model name).
- `ENABLE_EMBED_FALLBACK` — optional; set to `1` for demo if HF embedding calls are rate-limited.

Dependencies

Ensure `requirements.txt` (Space uses this) contains at least:

- streamlit
- requests
- numpy
- scikit-learn (optional — for cosine similarity helpers)
- pyyaml (optional)

If your existing `requirements.txt` already includes these, no change required. Avoid `faiss` unless you know it builds successfully in a Space.

Minimal code-conversion notes

1) Entrypoint

- Configure the Space to use `frontend/streamlit_app.py` (Streamlit).
- In the Streamlit app, import the helper functions from `backend/app/services/*` (embeddings, transcript chunking, simple retriever) and call them directly instead of calling FastAPI endpoints.

2) Embeddings

- Replace HTTP-only embedding calls with a small helper that calls Hugging Face Inference API using `requests` and `HF_API_TOKEN` from env. Example:

```python
import os
import requests

def get_hf_embedding(text: str, model: str = None) -> list[float]:
    token = os.getenv("HF_API_TOKEN")
    model = model or os.getenv("EMBED_MODEL") or "sentence-transformers/all-MiniLM-L6-v2"
    url = f"https://api-inference.huggingface.co/embeddings/{model}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(url, json={"inputs": text}, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]
```

- Keep `ENABLE_EMBED_FALLBACK` behavior: if HF fails and fallback is enabled, return a deterministic zero vector (or a small random vector with a fixed seed).

3) Small, dependency-free Retriever (in-memory)

- Avoid FAISS for the Space demo. Use numpy cosine similarity for small numbers of vectors. Example search:

```python
import numpy as np

def cosine_sim(query_vec, vectors, top_k=5):
    arr = np.array(vectors)  # shape (N, D)
    q = np.array(query_vec)
    norms = np.linalg.norm(arr, axis=1) * np.linalg.norm(q)
    scores = (arr @ q) / (norms + 1e-8)
    idx = np.argsort(scores)[-top_k:][::-1]
    return idx, scores[idx]
```

- Store vector metadata as a list of dicts in memory or as a file `vectorstore.json` under the repo (note: ephemeral between rebuilds).

4) Transcripts & chunking

- Reuse `backend/app/services/transcript.py` functions (`fetch_transcript`, `chunk_text`) by importing. If those functions call subprocesses (`yt_dlp`), ensure the Space provides that binary (might not). Alternative: use `youtube_transcript_api` pure Python library which works in Spaces.

5) LLM calls (Groq or other)

- Keep the `backend/app/services/llm.py` call patterns but switch to direct HTTP calls using secrets `GROQ_API_KEY`. Streamed responses may not work the same in Spaces; instead fetch full responses.

Example Groq call (simplified):

```python
import os
import requests

def query_groq(prompt: str):
    key = os.getenv("GROQ_API_KEY")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    url = "https://api.groq.ai/v1/models/<model>/generate"
    data = {"prompt": prompt, "max_tokens": 512}
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()
```

6) UI wiring

- Update `frontend/streamlit_app.py` so actions call in-process helpers:
  - `Ingest` button -> calls `fetch_transcript` -> `chunk_text` -> compute embeddings for chunks -> store vectors in memory or `vectorstore.json`.
  - `Query` -> compute embedding for query -> perform `cosine_sim` search -> assemble prompt with contexts -> call `query_groq` -> display answer.

7) Persistence and re-ingestion

- Because free Spaces are ephemeral, add an option in the UI to re-run ingest for a video id to restore vectors on each startup. Optionally save `vectorstore.json` to the Hugging Face Hub (via `huggingface_hub` API) or to S3 for persistence across restarts.

Deploy steps (Streamlit Space)

1. Create a new Space on Hugging Face: https://huggingface.co/new-space
   - Choose `Streamlit` as the SDK.
   - Link to this GitHub repository or push your code directly to the Space's git.
2. In the Space settings -> Secrets, add `HF_API_TOKEN`, `GROQ_API_KEY`, `EMBED_MODEL` etc.
3. Ensure `requirements.txt` includes required packages and push changes.
4. Set the Space `Hardware` to CPU (or GPU if needed and available).
5. Deploy and monitor the build logs. If a package fails to build (e.g., faiss), remove it and use the numpy fallback.

Quick checklist to prepare repo

- [ ] Add `get_hf_embedding` helper (or adapt `backend/app/services/embeddings.py`) so the Streamlit app can call it directly.
- [ ] Replace FAISS lookups with `cosine_sim` fallback for demos.
- [ ] Confirm `frontend/streamlit_app.py` imports the service functions directly and uses them.
- [ ] Add docs/secrets instructions (this file).
- [ ] Update `requirements.txt` with `streamlit`, `requests`, `numpy`, `scikit-learn` (optional).

Example small patch ideas (copy-paste)

- Add to top of `frontend/streamlit_app.py`:

```python
import os
from backend.app.services.transcript import fetch_transcript, chunk_text
from backend.app.services.embeddings import get_hf_embedding
from backend.app.services.llm import query_groq

# simple in-memory store
VECTORSTORE = {"vectors": [], "meta": []}

# on ingest
text = fetch_transcript(video_id)
chunks = chunk_text(text)
for chunk in chunks:
    emb = get_hf_embedding(chunk["text"])  # your helper
    VECTORSTORE["vectors"].append(emb)
    VECTORSTORE["meta"].append(chunk)
```

- Use `cosine_sim` search from this file when answering queries.

Final notes

- If you want, I can create a minimal `space/` example Streamlit app here that uses these fallbacks (no faiss, uses HF embeddings + in-memory similarity) and a `requirements-space.txt` tuned for Hugging Face Spaces. Tell me whether you prefer Streamlit or Gradio and I'll scaffold it.


