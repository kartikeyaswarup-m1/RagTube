import yt_dlp
import requests
import re
import json

def fetch_transcript(video_url: str) -> str:
    """
    Fetch transcript (manual or automatic subtitles) for a given YouTube video using yt_dlp.
    Returns the transcript as clean text, or an error message if unavailable.
    """
    ydl_opts = {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "skip_download": True,
        "subtitleslangs": ["en"],
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            # Try manual subtitles first
            subtitles = info.get("subtitles", {})
            # Fall back to auto-generated
            if not subtitles or "en" not in subtitles:
                subtitles = info.get("automatic_captions", {})

            if not subtitles or "en" not in subtitles:
                return "No transcript available for this video."

            # Grab the first available subtitle format (usually .vtt or .srv3)
            subtitle_url = subtitles["en"][0]["url"]
            response = requests.get(subtitle_url)
            if response.status_code != 200:
                return "Failed to fetch transcript."

            raw_text = response.text

            # Handle different caption formats
            if raw_text.strip().startswith("{"):
                # JSON-style captions (.srv3)
                try:
                    data = json.loads(raw_text)
                    texts = []
                    for ev in data.get("events", []):
                        for seg in ev.get("segs", []):
                            txt = seg.get("utf8", "").strip()
                            if txt:
                                texts.append(txt)
                    return " ".join(texts)
                except Exception:
                    pass

            # Clean WebVTT (remove timestamps & tags)
            cleaned = re.sub(r"<[^>]+>", "", raw_text)
            cleaned = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> .*", "", cleaned)
            cleaned = re.sub(r"^\s*\d+\s*$", "", cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r"\n+", "\n", cleaned).strip()

            return cleaned if cleaned else "Transcript is empty."

    except Exception as e:
        return f"Error fetching transcript: {str(e)}"

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Splits text into overlapping chunks for embedding.
    chunk_size and overlap are in characters (rough approximation of tokens).
    """
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = max(end - overlap, end)
    return chunks
