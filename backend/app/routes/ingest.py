import asyncio
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
from backend.app.services.transcript import (
    chunk_text,
    extract_video_id,
    fetch_transcript_data,
    manual_transcript_data,
)
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


async def _process_transcript_data(transcript_data: dict, video_url: str) -> dict:
    transcript = transcript_data.get("transcript", "")
    segments = transcript_data.get("segments", [])
    chunks = chunk_text(transcript, chunk_size=1000, overlap=200, segments=segments)
    if not chunks:
        raise HTTPException(status_code=422, detail=_failure_detail("EMPTY_TRANSCRIPT", "The transcript is empty."))

    try:
        await asyncio.to_thread(save_vectorstore, chunks)
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
    if transcript_data.get("status") != "ok":
        return {
            "video_url": video_url,
            "status": "transcript_unavailable",
            "source": "youtube",
            "error": transcript_data.get(
                "error",
                "Automatic transcript retrieval is unavailable from the deployed server.",
            ),
            "fallback": "manual_transcript",
            "transcript": "",
            "segments": [],
            "video_id": transcript_data.get("video_id") or extract_video_id(video_url),
            "title": transcript_data.get("title"),
            "thumbnail": transcript_data.get("thumbnail"),
        }
    return await _process_transcript_data(transcript_data, video_url)


@router.post("/manual")
async def ingest_manual_transcript(payload: ManualTranscriptRequest):
    video_url = payload.video_url.strip()
    transcript = payload.transcript.strip()
    video_id = extract_video_id(video_url)
    if not video_url or not video_id:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid YouTube video URL before processing a transcript.",
        )

    transcript_data = manual_transcript_data(transcript, video_url)
    if transcript_data.get("status") != "ok":
        raise HTTPException(status_code=400, detail=transcript_data.get("error", "Transcript is invalid."))

    result = await _process_transcript_data(transcript_data, video_url)
    result.update(
        {
            "source": "manual_transcript",
            "video_id": video_id,
            "title": f"YouTube video {video_id}",
            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        }
    )
    return result
