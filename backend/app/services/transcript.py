import yt_dlp
import requests
import re

def fetch_transcript(video_url: str) -> str:
    """
    Fetch transcript (manual or automatic subtitles) for a given YouTube video using yt_dlp.
    Returns the transcript as clean text, or an error message if unavailable.
    """
    ydl_opts = {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "skip_download": True,
        "subtitleslangs": ["en"],  # prioritize English
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

            # Grab the first available subtitle format (usually .vtt)
            subtitle_url = subtitles["en"][0]["url"]

            response = requests.get(subtitle_url)
            if response.status_code != 200:
                return "Failed to fetch transcript."

            raw_text = response.text

            # Clean WebVTT (remove timestamps & tags)
            cleaned = re.sub(r"<[^>]+>", "", raw_text)  # remove HTML tags
            cleaned = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> .*", "", cleaned)  # remove timestamps
            cleaned = re.sub(r"^\s*\d+\s*$", "", cleaned, flags=re.MULTILINE)  # remove subtitle indexes
            cleaned = re.sub(r"\n+", "\n", cleaned).strip()  # collapse multiple newlines

            return cleaned if cleaned else "Transcript is empty."

    except Exception as e:
        return f"Error fetching transcript: {str(e)}"