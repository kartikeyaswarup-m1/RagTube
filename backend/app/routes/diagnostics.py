from fastapi import APIRouter, Query
import socket
import requests
from backend.app.config import HF_API_TOKEN, EMBED_PROVIDER, GROQ_API_KEY, YOUTUBE_PROXY_URL
from backend.app.services.transcript import fetch_transcript_data

router = APIRouter()


@router.get("")
def diagnostics(video_url: str | None = Query(None, description="Optional public YouTube URL to test")):
    """Run basic DNS and HTTP connectivity checks from the running process.

    This is safe to expose temporarily on a deployed service to debug
    network/DNS/egress issues when a shell is not available.
    """
    result = {
        "env": {
            "embed_provider_set": bool(EMBED_PROVIDER),
            "hf_token_present": bool(HF_API_TOKEN),
            "groq_key_present": bool(GROQ_API_KEY),
            "youtube_proxy_configured": bool(YOUTUBE_PROXY_URL),
        },
        "checks": {},
    }

    host = "router.huggingface.co"
    # DNS resolution
    try:
        infos = socket.getaddrinfo(host, 443)
        addrs = sorted({f"{ai[4][0]}:{ai[4][1]}" for ai in infos})
        result["checks"]["dns"] = {"ok": True, "addresses": addrs}
    except Exception as e:
        result["checks"]["dns"] = {"ok": False, "error": str(e)}

    # HTTP reachability. A 2xx/3xx/4xx response still proves DNS and HTTPS work;
    # authentication/model errors are reported by the embedding request itself.
    try:
        resp = requests.get("https://router.huggingface.co", timeout=10)
        result["checks"]["http"] = {"ok": True, "status_code": resp.status_code, "reason": resp.reason}
    except Exception as e:
        result["checks"]["http"] = {"ok": False, "error": str(e)}

    if video_url:
        result["youtube"] = diagnose_transcript(video_url)

    return result


@router.get("/youtube")
def youtube_diagnostics(
    video_url: str = Query(
        "https://www.youtube.com/watch?v=2Xiljy4xzbc",
        description="Public YouTube URL to test without downloading media",
    ),
):
    return diagnose_transcript(video_url)


def diagnose_transcript(video_url: str) -> dict:
    result = fetch_transcript_data(video_url)
    return {
        "video_id": result.get("video_id"),
        "proxy_configured": bool(YOUTUBE_PROXY_URL),
        "transcript_api_available": True,
        "transcript_fetch": {
            "ok": result.get("status") == "ok",
            "segments": len(result.get("segments", [])),
            **({"error": result["error"]} if result.get("status") != "ok" else {}),
        },
    }
