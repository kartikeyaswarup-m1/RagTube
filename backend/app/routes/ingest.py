import asyncio
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from backend.app.services.transcript import fetch_transcript_data, manual_transcript_data, chunk_text
from backend.app.services.retriever import save_vectorstore
from backend.app.services.embeddings import EmbeddingError

router = APIRouter()


class ManualTranscriptRequest(BaseModel):
    video_url: str = ""
    transcript: str = Field(..., min_length=1, max_length=1_000_000)


def _failure_detail(code: str, message: str, fallback: str | None = None) -> dict:
    detail = {"code": code, "message": message}
    if fallback:
        detail["fallback"] = fallback
    return detail


def _process_transcript_data(transcript_data: dict, video_url: str) -> dict:
    if transcript_data.get("status") != "ok":
        raise HTTPException(
            status_code=422,
            detail=_failure_detail(
                "TRANSCRIPT_UNAVAILABLE",
                transcript_data.get("error", "Automatic YouTube transcript retrieval is unavailable from the deployed server."),
                "manual_transcript",
            ),
        )

    transcript = transcript_data.get("transcript", "")
    segments = transcript_data.get("segments", [])
    chunks = chunk_text(transcript, chunk_size=1000, overlap=200, segments=segments)
    if not chunks:
        raise HTTPException(status_code=422, detail=_failure_detail("EMPTY_TRANSCRIPT", "The transcript is empty."))

    try:
        save_vectorstore(chunks)
    except EmbeddingError as error:
        raise HTTPException(status_code=502, detail=_failure_detail("EMBEDDING_FAILED", str(error))) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=_failure_detail("VECTORSTORE_FAILED", "Failed to build the FAISS vector store.")) from error

    return {
        "video_url": video_url,
        "status": "ingested",
        "chunks": len(chunks),
        "transcript": transcript,
        "segments": segments,
        "video_id": transcript_data.get("video_id"),
        "title": transcript_data.get("title"),
        "thumbnail": transcript_data.get("thumbnail"),
    }

@router.get("")
async def ingest_video(video_url: str = Query(..., description="YouTube video URL")):
    """Ingest a YouTube video transcript and build a FAISS index.
    
    Uses asyncio.to_thread to run blocking transcript API I/O in a thread
    pool, preventing the event loop from hanging.
    """
    # Run the blocking fetch_transcript_data in a thread pool
    transcript_data = await asyncio.to_thread(fetch_transcript_data, video_url)
    return _process_transcript_data(transcript_data, video_url)


@router.post("/transcript")
async def ingest_manual_transcript(payload: ManualTranscriptRequest):
    transcript_data = manual_transcript_data(payload.transcript, payload.video_url)
    return _process_transcript_data(transcript_data, payload.video_url)
