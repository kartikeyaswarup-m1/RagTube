# Free Deployment: Cloudflare Pages + Render

This is the deployment path for the production application in this repository:

- Frontend: React + Vite on Cloudflare Pages Free
- Backend: FastAPI using `backend/Dockerfile` on Render Free Web Service
- Generation: Groq API free tier
- Embeddings: Hugging Face Inference API
- Retrieval: FAISS stored on the backend filesystem

This setup uses the free `*.pages.dev` and `*.onrender.com` domains. No paid database, vector database, domain, VPS, or cloud account is required. Free-tier availability and provider rate limits can change, so verify the current provider terms when creating accounts.

## Prerequisites

- GitHub account with this repository pushed
- Groq API key
- Hugging Face access token with inference permissions
- Cloudflare account
- Render account
- Node.js 18+ and Python 3.10+ for local testing

Never commit API keys. The repository ignores `.env` files; use `.env.example` as the safe template.

## 1. Deploy the backend to Render

1. Open the Render dashboard and choose **New > Web Service**.
2. Connect the GitHub repository.
3. Select **Docker** as the runtime.
4. Use the repository root as the service root/context.
5. Set the Dockerfile path to `backend/Dockerfile`.
6. Choose the **Free** instance type.
7. Add these environment variables in Render:

   | Variable | Value |
   | --- | --- |
   | `LLM_PROVIDER` | `groq` |
   | `GROQ_API_KEY` | Your Groq key, entered privately in Render |
   | `GROQ_MODEL` | `llama-3.1-8b-instant` |
   | `EMBED_PROVIDER` | `hf` |
   | `HF_API_TOKEN` | Your Hugging Face token, entered privately in Render |
   | `HF_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
   | `VECTORSTORE_DIR` | `/app/backend/vectorstore` |
   | `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` initially |

Render supplies `PORT` automatically. The Dockerfile starts Uvicorn on `0.0.0.0:$PORT`; do not add a fixed production port.

After deployment, copy the backend URL, for example `https://your-backend.onrender.com`.

## 2. Test the backend

Replace the URL in these commands with your Render URL:

```bash
curl https://your-backend.onrender.com/
curl https://your-backend.onrender.com/health
curl https://your-backend.onrender.com/diagnostics/youtube
open https://your-backend.onrender.com/docs
```

`/health` returns `ok` when provider credentials are present and `degraded` with the missing variable names when they are not. It never returns secret values.

## 3. Deploy the frontend to Cloudflare Pages

1. Open Cloudflare Dashboard > **Workers & Pages** > **Create application** > **Pages**.
2. Connect the same GitHub repository.
3. Set **Root directory** to `frontend`.
4. Set **Build command** to `npm run build`.
5. Set **Output directory** to `dist`.
6. Add the production environment variable:

   ```text
   VITE_API_BASE=https://your-backend.onrender.com
   ```

7. Deploy the site and copy its `https://your-project.pages.dev` URL.

Vite reads `VITE_API_BASE` at build time. The local fallback remains `http://127.0.0.1:8000` only when the variable is absent.

## 4. Finish CORS configuration

Go back to the Render service and set:

```text
CORS_ORIGINS=https://your-project.pages.dev
```

You may keep the localhost origins too while developing:

```text
CORS_ORIGINS=https://your-project.pages.dev,http://localhost:5173,http://127.0.0.1:5173
```

Redeploy the backend after changing the variable. Do not use `*` for the production frontend.

## 5. End-to-end test

1. Open the Cloudflare Pages URL.
2. Paste a public YouTube URL into **Ingest a video**.
3. Click **Ingest video** and wait for the transcript/chunk count.
4. Enter a question in **Chat about the video**.
5. Click **Send** and verify that the streamed answer appears.

If ingestion fails, first open `/health`, then inspect the Render logs for transcript, Hugging Face, or Groq errors. Use a public video with captions for the first test.

The YouTube diagnostic exercises the same `youtube-transcript-api` path used by ingestion and reports the video ID, whether the API fetch succeeded, the segment count, and a safe error when it failed. It never returns cookies, API keys, or request headers.

## Free-tier limitations

- Render Free services can sleep after inactivity; the first request after sleep may be slow.
- Render Free filesystem storage is ephemeral. `faiss.index`, `mapping.pkl`, and transcript fallback files can disappear after restart or redeploy.
- Ingest the video again whenever the vector store is missing.
- Groq and Hugging Face free APIs have quotas, rate limits, and model availability constraints.
- YouTube transcripts can be unavailable for private, age-restricted, geo-blocked, or captionless videos.
- This deployment is suitable for a portfolio, demo, or college project rather than high traffic or durable multi-user storage.

## Local verification

```bash
cp .env.example backend/.env
# Edit backend/.env and add GROQ_API_KEY and HF_API_TOKEN.
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.
