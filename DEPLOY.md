# Deployment Guide

This document explains two pieces:

- Deploy the `frontend` to Cloudflare Pages (static site)
- Deploy the `backend` (FastAPI) to a free-tier host (Railway/Render) using Docker or `Procfile` and a Hugging Face backend option

**Frontend — Cloudflare Pages**

1. In your GitHub/Git provider, push the repo.
2. Go to Cloudflare dashboard → Pages → Create a project.
3. Connect your repository and select the `frontend` folder as the project root.
4. Build settings (Vite):
   - Framework preset: `Vite`
   - Build command: `npm run build`
   - Build output directory: `dist`
5. Set environment variables if your frontend needs to call a remote backend (e.g., `REACT_APP_API_URL` or similar).
6. Deploy — Cloudflare will build and publish your frontend on a CDN.

Optional: Use Cloudflare Tunnel to expose a local backend while developing.

**Backend — Railway / Render / Replit (free-tier)**

Option A — Quick (use Dockerfile):

- Railway and Render both support deploying from a Dockerfile. In the project settings, set environment variables and point the service to use the `backend/Dockerfile`.

Option B — Quick (use Procfile / buildpacks):

- Some platforms detect Python FastAPI via a `Procfile`. If using Railway or Heroku-style deploys, the included `backend/Procfile` will run the app.

Required environment variables (set these in your host dashboard):

- `LLM_PROVIDER` — `hf` or `ollama` or `groq`
- If using Ollama remotely: `OLLAMA_HOST`, `OLLAMA_MODEL`
- If using Hugging Face: `HF_API_TOKEN`, `HF_MODEL` (model id), `HF_EMBED_MODEL` (embedding model id)
- `EMBED_PROVIDER` (optional) — `hf` to force embeddings via HF
- `VECTORSTORE_DIR` — path for FAISS files (ensure writable volume or use ephemeral/remote vectorstore)
- `GROQ_API_KEY` / `GROQ_MODEL` if using Groq

Notes & tradeoffs:

- Ollama is designed to run locally; deploying it in free cloud is not practical. Switch to `hf` (Hugging Face) or `groq` for cloud deploys.
- Persisting `faiss.index` requires writable persistent storage; configure volumes in Render/Railway or store vectors in a cloud datastore.

**Deploy steps (Railway example)**

1. Create a new project on Railway and connect your repo.
2. Add a new service, choose Docker deploy and point to `backend/Dockerfile`.
3. Set environment variables (see list above).
4. Deploy and inspect logs; visit the assigned URL.

If you'd like, I can:

- Add a simple `hf` provider implementation (done) and update `embeddings` to use Hugging Face (done).
- Walk through configuring a Railway or Render project with screenshots and exact env values.

