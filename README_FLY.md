Fly.io deployment guide for RagTube

1) Install flyctl

  https://fly.io/docs/hands-on/install-flyctl/

2) Build & test locally with Docker

  # build image
  docker build -t ragtube:local .

  # run locally (bind port 8080)
  docker run --rm -p 8080:8080 -e ENABLE_EMBED_FALLBACK=1 ragtube:local

3) Create and deploy on Fly

  # login and create app (follow prompts)
  flyctl launch --name ragtube --region iad --port 8080

  # set secrets (replace with your tokens)
  flyctl secrets set HF_API_TOKEN="<your_hf_token>" GROQ_API_KEY="<your_groq_key>" \
    EMBED_PROVIDER=hf LLM_PROVIDER=groq

  # (optional) enable dev fallback while fixing networking
  flyctl secrets set ENABLE_EMBED_FALLBACK=1

  # deploy
  flyctl deploy

4) Verify

  # check app status
  flyctl status

  # call diagnostics endpoint
  curl -sS https://<your-fly-app>.fly.dev/diagnostics | jq

5) Optional: persist vectorstore (volumes)

  # create volume
  flyctl volumes create ragtube-vectorstore --region iad --size 1

  # add to fly.toml mounts section (flyctl may prompt to add)

Notes
- The Dockerfile uses a slim Python image and installs minimal build deps; adjust if you hit build errors for `faiss-cpu` on your chosen platform.
- Disable `ENABLE_EMBED_FALLBACK` in production to use real embeddings.
