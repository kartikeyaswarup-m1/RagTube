# from fastapi import APIRouter, Query
# from backend.app.services.transcript import fetch_transcript

# router = APIRouter()

# # NOTE: no '/ingest' here; main.py already prefixes this router with '/ingest'
# @router.get("")
# async def ingest_video(video_url: str = Query(..., description="YouTube video URL")):
#     transcript = fetch_transcript(video_url)
#     return {"video_url": video_url, "transcript": transcript}
from fastapi import APIRouter, Query
from backend.app.services.transcript import fetch_transcript, chunk_text
from backend.app.services.retriever import save_vectorstore

router = APIRouter()

@router.get("")
async def ingest_video(video_url: str = Query(..., description="YouTube video URL")):
    transcript = fetch_transcript(video_url)
    if not transcript or "Error" in transcript or "No transcript" in transcript:
        return {"video_url": video_url, "status": "failed", "transcript": transcript}

    # Step 1 — Chunk the transcript
    chunks = chunk_text(transcript, chunk_size=1000, overlap=200)

    # Step 2 — Save chunks to FAISS
    try:
        save_vectorstore(chunks)
        return {"video_url": video_url, "status": "ingested", "chunks": len(chunks)}
    except Exception as e:
        return {"video_url": video_url, "status": "error", "error": str(e)}
