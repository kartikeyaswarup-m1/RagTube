import streamlit as st
import requests
import json
import os

# Config
BACKEND = os.getenv("ST_BACKEND_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="RagTube", layout="centered", initial_sidebar_state="expanded")

# Minimal styling
st.markdown("""
<style>
* { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
body, [data-testid="stAppViewContainer"] {
    background-color: #0f0f0f;
    color: #e5e5e5;
}
h1 { font-size: 28px; font-weight: 700; margin: 0; color: #e5e5e5; }
h2 { font-size: 14px; font-weight: 500; color: #888; margin: 16px 0 8px 0; }
.stTextInput input, .stTextArea textarea {
    background-color: #1a1a1a !important;
    border: 1px solid #333 !important;
    border-radius: 6px !important;
    color: #e5e5e5 !important;
    font-size: 14px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border: 1px solid #666 !important;
    box-shadow: none !important;
}
.stButton button {
    background-color: #fff;
    color: #000;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    font-size: 14px;
}
.stButton button:hover {
    background-color: #ccc;
}
.message-user {
    background-color: #1a1a1a;
    padding: 12px 14px;
    border-radius: 8px;
    margin: 8px 0;
    color: #e5e5e5;
}
.message-assistant {
    background-color: #0f0f0f;
    padding: 12px 14px;
    margin: 8px 0;
    color: #e5e5e5;
    line-height: 1.5;
}
.stInfo, .stWarning, .stError {
    background-color: #1a1a1a !important;
    border: 1px solid #333 !important;
    border-radius: 6px !important;
    padding: 12px !important;
    color: #e5e5e5 !important;
}
</style>
""", unsafe_allow_html=True)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "video" not in st.session_state:
    st.session_state.video = None

def extract_video_id(url: str) -> str:
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    return url[:11]

# Sidebar
with st.sidebar:
    st.markdown("## Previous Queries")
    if st.session_state.messages:
        count = 0
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                q = msg["content"][:50]
                st.caption(f"• {q}...")
                count += 1
                if count >= 8:
                    break
    else:
        st.caption("No queries yet")
    if st.button("Clear History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Header
st.markdown("# RagTube")
st.markdown("Ask questions about YouTube Lectures and Videos")
st.markdown("---")

# Ingest
st.markdown("## Load Video")
url = st.text_input("YouTube URL", placeholder="https://youtube.com/watch?v=...", label_visibility="collapsed")
if st.button("Load", use_container_width=True):
    if url:
        with st.spinner("Processing..."):
            try:
                r = requests.get(f"{BACKEND}/ingest", params={"video_url": url}, timeout=300)
                d = r.json()
                if r.status_code == 200:
                    st.session_state.video = {"id": extract_video_id(url), "chunks": d.get("chunks", 0)}
                    st.success(f"Loaded: {d['chunks']} chunks")
                else:
                    st.error(d.get("transcript", "Error"))
            except Exception as e:
                st.error(str(e))
    else:
        st.error("Enter a URL")

if st.session_state.video:
    st.caption(f"Video: {st.session_state.video['id']} • {st.session_state.video['chunks']} chunks")
else:
    st.caption("No video loaded")

st.markdown("---")

# Chat
st.markdown("## Chat")
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}", unsafe_allow_html=True)
    else:
        st.markdown(f"{msg['content']}", unsafe_allow_html=True)
st.markdown("---")

# Query
q = st.text_input("Question", placeholder="Ask something...", label_visibility="collapsed")
if st.button("Send", use_container_width=True):
    if not q:
        st.error("Enter a question")
    elif not st.session_state.video:
        st.error("Load a video first")
    else:
        st.session_state.messages.append({"role": "user", "content": q})
        with st.spinner("Thinking..."):
            try:
                r = requests.get(f"{BACKEND}/query", params={"question": q}, stream=True, timeout=120)
                if r.status_code == 200:
                    answer = ""
                    for line in r.iter_lines(decode_unicode=True):
                        if line:
                            try:
                                obj = json.loads(line)
                                if "text" in obj:
                                    answer += obj["text"]
                                elif obj.get("done"):
                                    break
                            except:
                                pass
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error("Query failed")
            except Exception as e:
                st.error(str(e))
        st.rerun()
