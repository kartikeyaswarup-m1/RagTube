from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys, os

# Make sure rag_backend.py is importable from the same folder
sys.path.append(os.path.dirname(__file__))
import rag_backend as rag

# ── App setup ─────────────────────────────────────────────────────────────────
# FastAPI() creates your web server.
# Think of it as opening a restaurant — now you need to add menu items (routes).
app = FastAPI()

# CORS = Cross Origin Resource Sharing.
# By default browsers BLOCK a website from calling a different server.
# Our React app runs on localhost:5173, our FastAPI runs on localhost:8000.
# These are "different origins" so we must explicitly allow it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server address
    allow_methods=["*"],    # allow GET, POST, etc.
    allow_headers=["*"],
)

# ── Request models ─────────────────────────────────────────────────────────────
# Pydantic models define the shape of data coming IN from React.
# FastAPI uses these to automatically validate the request body.
# If React sends wrong data, FastAPI rejects it with a clear error.

class VideoRequest(BaseModel):
    url: str           # React will send { "url": "https://youtube.com/..." }

class AskRequest(BaseModel):
    question: str      # React will send { "question": "...", "query_type": "...", ... }
    query_type: str
    video_url: str
    chat_history: list  # list of [role, message] pairs


# ── Routes (endpoints) ────────────────────────────────────────────────────────
# A route is a URL + HTTP method that triggers a Python function.
# @app.post("/load-video") means: when React sends a POST request to
# http://localhost:8000/load-video, run the function below it.

@app.post("/load-video")
def load_video(req: VideoRequest):
    """
    React sends the YouTube URL.
    We call rag_backend.load_video() and return success or error.
    """
    result = rag.load_video(req.url)
    if result is not None:
        # result is an error string
        return {"success": False, "error": result}
    return {"success": True}


@app.post("/classify")
def classify(req: VideoRequest):
    """
    React sends the question (reusing VideoRequest since it just has one string field).
    We classify it and return SUMMARY / LISTING / SPECIFIC.
    This lets React show the right loading message before calling /ask.
    """
    query_type = rag.classify_query(req.url)   # url field reused for question string
    return {"query_type": query_type}


@app.post("/ask")
def ask(req: AskRequest):
    """
    React sends the question + context.
    We call rag_backend.ask_question() and return the answer + sources.
    """
    answer, sources, rewritten = rag.ask_question(
        req.question,
        req.chat_history,
        req.query_type,
        req.video_url,
    )

    # Convert sources to a JSON-serializable format
    # (tuples aren't valid JSON, so we convert to dicts)
    sources_json = [
        {"text": text, "score": round(float(score), 2), "start": int(start)}
        for text, score, start in sources
    ]

    return {
        "answer": answer,
        "sources": sources_json,
        "rewritten_query": rewritten,
    }


@app.post("/clear")
def clear_history():
    """
    React calls this when the user clicks 'Clear Conversation'.
    Nothing to do on the backend since chat_history lives in React state.
    Just a clean hook in case we need server-side cleanup later.
    """
    return {"success": True}


# ── Run ───────────────────────────────────────────────────────────────────────
# This block only runs if you execute `python main.py` directly.
# Normally you run: uvicorn main:app --reload
# --reload means: restart the server automatically when you save a file.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)