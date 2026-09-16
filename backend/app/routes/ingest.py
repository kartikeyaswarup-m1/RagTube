import asyncio
from fastapi import APIRouter, HTTPException, Query
from backend.app.services.transcript import fetch_transcript_data, chunk_text
from backend.app.services.retriever import save_vectorstore
from backend.app.services.embeddings import EmbeddingError

router = APIRouter()

@router.get("")
async def ingest_video(video_url: str = Query(..., description="YouTube video URL")):
    """Ingest a YouTube video transcript and build a FAISS index.
    
    Uses asyncio.to_thread to run blocking I/O (yt_dlp, network requests) in a thread
    pool, preventing the event loop from hanging.
    """
    # Run the blocking fetch_transcript_data in a thread pool
    transcript_data = await asyncio.to_thread(fetch_transcript_data, video_url)
    transcript = transcript_data.get("transcript", "")

    original_status = transcript_data.get("status")
    if original_status != "ok":
        raise HTTPException(
            status_code=422,
            detail=transcript_data.get("error", "Unable to retrieve a transcript for this video."),
        )

    # Step 1 — Chunk the transcript into timestamped chunks (if segments available)
    segments = transcript_data.get("segments", [])
    chunks = chunk_text(transcript, chunk_size=1000, overlap=200, segments=segments)

    # Step 2 — Save chunks to FAISS (if embeddings configured)
    try:
        # Save timestamped chunks (each chunk may be a dict with text/start/end)
        save_vectorstore(chunks)
        return {
            "video_url": video_url,
            "status": "ingested",
            "chunks": len(chunks),
            "transcript": transcript,
            "segments": transcript_data.get("segments", []),
            "video_id": transcript_data.get("video_id"),
            "title": transcript_data.get("title"),
            "thumbnail": transcript_data.get("thumbnail"),
        }
    except EmbeddingError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Failed to build the FAISS vector store.") from error
