from fastapi import APIRouter, Query
from backend.app.services.transcript import fetch_transcript

router = APIRouter()

# NOTE: no '/ingest' here; main.py already prefixes this router with '/ingest'
@router.get("")
async def ingest_video(video_url: str = Query(..., description="YouTube video URL")):
    transcript = fetch_transcript(video_url)
    return {"video_url": video_url, "transcript": transcript}