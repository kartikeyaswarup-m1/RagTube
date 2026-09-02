import os
import streamlit as st
import requests
import numpy as np
from youtube_transcript_api import YouTubeTranscriptApi


def fetch_transcript(video_id: str) -> str:
    try:
        parts = YouTubeTranscriptApi.get_transcript(video_id)
        texts = [p.get("text", "") for p in parts]
        return "\n".join(texts)
    except Exception as e:
        return f"ERROR_FETCHING_TRANSCRIPT: {e}"


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200):
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        j = min(i + chunk_size, n)
        chunk = text[i:j]
        chunks.append({"text": chunk, "start_char": i, "end_char": j})
        i = j - overlap
        if i < 0:
            i = 0
    return chunks


def get_hf_embedding(text: str, model: str | None = None) -> list[float]:
    token = os.getenv("HF_API_TOKEN")
    model = model or os.getenv("EMBED_MODEL") or "sentence-transformers/all-MiniLM-L6-v2"
    url = f"https://api-inference.huggingface.co/embeddings/{model}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        resp = requests.post(url, json={"inputs": text}, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("embedding") or data.get("data", [])[0].get("embedding")
    except Exception:
        if os.getenv("ENABLE_EMBED_FALLBACK") == "1":
            return [0.0] * 384
        raise


def cosine_sim(query_vec, vectors, top_k=5):
    arr = np.array(vectors)
    q = np.array(query_vec)
    norms = np.linalg.norm(arr, axis=1) * (np.linalg.norm(q) + 1e-12)
    scores = (arr @ q) / (norms + 1e-12)
    idx = np.argsort(scores)[-top_k:][::-1]
    return idx, scores[idx]


def query_groq(prompt: str) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return "(no GROQ key configured) \n\nPrompt sent:\n" + prompt[:2000]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    url = os.getenv("GROQ_URL") or "https://api.groq.ai/v1/models/groq2-mini/generate"
    payload = {"prompt": prompt, "max_tokens": 512}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # try several response shapes
    if isinstance(data, dict):
        return data.get("text") or str(data)
    return str(data)


def main():
    st.title("RagTube — Hugging Face Space (demo)")

    st.sidebar.header("Settings")
    enable_fallback = st.sidebar.checkbox("Enable embed fallback", value=True)
    if enable_fallback:
        os.environ["ENABLE_EMBED_FALLBACK"] = "1"

    st.markdown("Enter a YouTube video id (the part after `v=` in the URL), ingest, then ask questions.")
    video_id = st.text_input("YouTube video id")

    if st.button("Ingest"):
        if not video_id:
            st.error("Provide a video id first")
        else:
            with st.spinner("Fetching transcript and creating vectors..."):
                text = fetch_transcript(video_id)
                if text.startswith("ERROR_FETCHING_TRANSCRIPT"):
                    st.error(text)
                    return
                chunks = chunk_text(text)
                vectors = []
                meta = []
                for c in chunks:
                    try:
                        emb = get_hf_embedding(c["text"]) or [0.0] * 384
                    except Exception as e:
                        st.warning(f"Embedding failed: {e}")
                        emb = [0.0] * 384
                    vectors.append(emb)
                    meta.append(c)
                st.session_state["vectors"] = vectors
                st.session_state["meta"] = meta
                st.success(f"Ingested {len(meta)} chunks")

    if st.session_state.get("meta"):
        st.subheader("Ingested chunks (preview)")
        for i, m in enumerate(st.session_state["meta"][:5]):
            st.markdown(f"**{i}**: {m['text'][:200].replace('\n',' ')}...")

    question = st.text_input("Ask a question")
    if st.button("Query"):
        if not question:
            st.error("Type a question")
        elif not st.session_state.get("vectors"):
            st.error("No vectors — run Ingest first")
        else:
            with st.spinner("Computing answer..."):
                q_emb = get_hf_embedding(question)
                idxs, scores = cosine_sim(q_emb, st.session_state["vectors"], top_k=5)
                contexts = []
                for idx in idxs:
                    contexts.append(st.session_state["meta"][int(idx)]["text"])
                prompt = "Answer the question based on these contexts:\n\n" + "\n\n---\n\n".join(contexts) + "\n\nQuestion: " + question
                ans = query_groq(prompt)
                st.subheader("Answer")
                st.write(ans)


if __name__ == "__main__":
    if "vectors" not in st.session_state:
        st.session_state["vectors"] = []
        st.session_state["meta"] = []
    main()
