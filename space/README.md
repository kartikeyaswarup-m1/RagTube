# RagTube — Hugging Face Space

This folder contains a minimal Streamlit app and requirements to run RagTube as a Hugging Face Space demo.

How to use

1. Create a new Space on Hugging Face and choose `Streamlit` as the SDK.
2. Push this `space/` folder to the Space's Git repository (or copy these files into the Space).
3. In the Space settings -> Secrets, add `HF_API_TOKEN` and `GROQ_API_KEY` (optional). Optionally set `EMBED_MODEL`.
4. Deploy — the Space will install packages from `requirements-space.txt` and run `streamlit_app.py`.

Notes

- This demo uses in-memory vector storage; it is ephemeral across restarts.
- For production or larger datasets, replace the in-memory `cosine_sim` with `faiss` and persist vectors to S3 or an external store.
