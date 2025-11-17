import streamlit as st
import requests
import os
from typing import List

# Config
DEFAULT_BACKEND = os.getenv("ST_BACKEND_URL", "http://127.0.0.1:8000")
BACKEND_INGEST = DEFAULT_BACKEND + "/ingest"
BACKEND_QUERY = DEFAULT_BACKEND + "/query"

st.set_page_config(page_title="RagTube UI", layout="wide")

st.title("RagTube — Streamlit UI")

tabs = st.tabs(["Ingest", "Query", "Vectorstore"])

# Ingest tab
with tabs[0]:
    st.header("Ingest YouTube Video")
    video_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
    col1, col2 = st.columns([3,1])
    with col1:
        ingest_btn = st.button("Ingest video")
    with col2:
        clear_history = st.button("Clear history")

    # simple history stored in session_state
    if "ingest_history" not in st.session_state:
        st.session_state.ingest_history = []

    if clear_history:
        st.session_state.ingest_history = []
        st.success("History cleared")

    if ingest_btn:
        if not video_url.strip():
            st.error("Please paste a YouTube URL first.")
        else:
            params = {"video_url": video_url.strip()}
            with st.spinner("Ingesting video (fetch transcript, chunk, create embeddings)..."):
                try:
                    resp = requests.get(BACKEND_INGEST, params=params, timeout=300)
                    data = resp.json()
                    if resp.status_code == 200 and data.get("status") == "ingested":
                        st.success(f"Ingested: {data.get('chunks')} chunks")
                        st.session_state.ingest_history.insert(0, {"url": video_url, "chunks": data.get("chunks")})
                    else:
                        # show helpful error info (fetch_transcript may return string)
                        st.error(f"Ingest failed: {data}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")

    if st.session_state.ingest_history:
        st.subheader("Recent ingests")
        for entry in st.session_state.ingest_history[:10]:
            st.write(f"- `{entry['url']}` — chunks: {entry['chunks']}")

# Query tab
with tabs[1]:
    st.header("Ask a question about the last ingested video")
    question = st.text_input("Your question", placeholder="What is this video about?")
    top_k = st.slider("Retrieve top K contexts", min_value=1, max_value=10, value=3)
    ask_btn = st.button("Ask")

    if ask_btn:
        if not question.strip():
            st.error("Please type a question.")
        else:
            params = {"question": question.strip()}
            with st.spinner("Querying vectorstore and LLM..."):
                try:
                    resp = requests.get(BACKEND_QUERY, params=params, timeout=120)
                    data = resp.json()
                    if resp.status_code == 200 and "answer" in data:
                        st.subheader("Answer")
                        st.write(data["answer"])
                    else:
                        st.error(f"Query failed: {data}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")

# Vectorstore tab (status & debug)
with tabs[2]:
    st.header("Vectorstore / Debug")
    st.write("This shows local files and a quick test for retrieval.")

    check_btn = st.button("Check vectorstore files")
    if check_btn:
        try:
            # Ask backend indirectly by trying a small query (backend will error if not present)
            resp = requests.get(BACKEND_QUERY, params={"question":"__VECTORSTORE_CHECK__"}, timeout=10)
            data = resp.json()
            st.json(data)
        except requests.exceptions.RequestException as e:
            st.error(f"Request failed: {e}")
            st.info("Make sure the backend is running and you have ingested at least one video.")