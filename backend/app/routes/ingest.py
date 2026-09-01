import asyncio
from fastapi import APIRouter, Query
from backend.app.services.transcript import fetch_transcript_data, chunk_text
from backend.app.services.retriever import save_vectorstore
from backend.app.config import VECTORSTORE_DIR
import pickle

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

    # If the transcript fetch reported a non-ok status but still returned
    # transcript content (some yt_dlp cases), continue so we can at least
    # provide the transcript and segments to the frontend. Otherwise return
    # the original error immediately.
    original_status = transcript_data.get("status")
    if original_status != "ok" and not transcript:
        return {
            "video_url": video_url,
            "status": transcript_data.get("status", "failed"),
            "transcript": transcript,
            "error": transcript_data.get("error", transcript),
            "segments": transcript_data.get("segments", []),
            "video_id": transcript_data.get("video_id"),
            "title": transcript_data.get("title"),
            "thumbnail": transcript_data.get("thumbnail"),
        }

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
    except Exception as e:
        # If embeddings are not configured (common on cloud deploys),
        # don't treat this as a hard failure — return a successful ingest
        # response but include a `warning` so callers can surface guidance.
        err_str = str(e)
        if "No supported embedding provider" in err_str or "HF_API_TOKEN" in err_str or "EMBED_PROVIDER" in err_str:
            # Persist mapping.pkl so queries can still use transcript segments
            mapping_file = VECTORSTORE_DIR / "mapping.pkl"
            transcript_file = None
            try:
                if transcript_data.get("video_id"):
                    transcript_file = VECTORSTORE_DIR / f"transcript_{transcript_data.get('video_id')}.json"

                with open(mapping_file, "wb") as f:
                    pickle.dump(chunks, f)

                if transcript_file:
                    # persist transcript and segments for reliable fallback
                    with open(transcript_file, "w", encoding="utf-8") as tf:
                        import json as _json

                        _json.dump({
                            "transcript": transcript,
                            "segments": transcript_data.get("segments", []),
                            "video_id": transcript_data.get("video_id"),
                            "title": transcript_data.get("title"),
                            "thumbnail": transcript_data.get("thumbnail"),
                        }, tf)
            except Exception:
                # non-fatal: if mapping/transcript cannot be written, still return transcript
                pass

            return {
                "video_url": video_url,
                "status": "ingested",
                "chunks": len(chunks),
                "transcript": transcript,
                "segments": transcript_data.get("segments", []),
                "video_id": transcript_data.get("video_id"),
                "title": transcript_data.get("title"),
                "thumbnail": transcript_data.get("thumbnail"),
                "warning": err_str,
            }

        # otherwise surface the error as before
        return {
            "video_url": video_url,
            "status": "error",
            "error": err_str,
            "transcript": transcript,
            "segments": transcript_data.get("segments", []),
            "video_id": transcript_data.get("video_id"),
            "title": transcript_data.get("title"),
            "thumbnail": transcript_data.get("thumbnail"),
        }
