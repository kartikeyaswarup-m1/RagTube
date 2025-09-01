from fastapi import APIRouter, Query
from app.services.transcript import fetch_transcript

router = APIRouter()

@router.get("/ingest")
async def ingest_video(video_url: str = Query(..., description="YouTube video URL")):
    transcript = fetch_transcript(video_url)
    return {"video_url": video_url, "transcript": transcript}