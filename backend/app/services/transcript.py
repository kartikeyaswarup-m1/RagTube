import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import (
    NoTranscriptFound,
    YouTubeTranscriptApi,
    YouTubeTranscriptApiException,
)


def _normalize_youtube_url(video_url: str) -> str:
    """Normalize supported YouTube URLs to a canonical watch URL."""
    parsed = urlparse(video_url)

    if "youtube.com" not in parsed.netloc and "youtu.be" not in parsed.netloc:
        return video_url

    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.lstrip("/")
        return f"https://www.youtube.com/watch?v={video_id}"

    query = parse_qs(parsed.query)
    video_id = query.get("v", [""])[0]
    if not video_id:
        return video_url

    return f"https://www.youtube.com/watch?v={video_id}"


def extract_video_id(video_url: str) -> str:
    """Extract a video ID from common YouTube URL formats.

    Keeping this in the transcript service means automatic and pasted
    transcript ingestion validate URLs the same way.
    """
    try:
        parsed = urlparse(video_url.strip())
        hostname = parsed.netloc.lower()
    except (AttributeError, ValueError):
        return ""

    if hostname == "youtu.be" or hostname.endswith(".youtu.be"):
        return parsed.path.strip("/").split("/")[0]

    if "youtube.com" in hostname:
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if video_id:
            return video_id
        match = re.match(r"^/(?:shorts|embed|live)/([^/?]+)", parsed.path)
        if match:
            return match.group(1)

    return ""


def fetch_transcript_data(video_url: str) -> dict:
    """
    Fetch transcript metadata and timestamped cues for a given YouTube video.
    Returns a dictionary with transcript text, cue data, and video metadata.
    """
    try:
        normalized_url = _normalize_youtube_url(video_url)
        video_id = extract_video_id(normalized_url)
        if not video_id:
            return _transcript_error("Enter a valid YouTube video URL.")

        api = YouTubeTranscriptApi()
        transcript_list = list(api.list(video_id))
        preferred = [
            item for item in transcript_list
            if item.language_code.startswith("en") and not item.is_generated
        ]
        generated = [
            item for item in transcript_list
            if item.language_code.startswith("en") and item.is_generated
        ]
        candidates = preferred or generated or transcript_list
        if not candidates:
            return _transcript_error("No transcript or captions are available for this video.", video_id)

        fetched = candidates[0].fetch()
        segments = [
            {
                "start": float(snippet.start),
                "end": float(snippet.start + snippet.duration),
                "text": snippet.text.strip(),
            }
            for snippet in fetched.snippets
            if snippet.text.strip()
        ]
        transcript = " ".join(segment["text"] for segment in segments).strip()
        if not segments:
            return _transcript_error("No transcript or captions are available for this video.", video_id)

        return {
            "status": "ok",
            "transcript": transcript,
            "segments": segments,
            "video_id": video_id,
            "title": None,
            "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        }

    except NoTranscriptFound:
        return _transcript_error("No transcript or captions are available for this video.", video_id)
    except YouTubeTranscriptApiException as error:
        return _transcript_error(_safe_transcript_error(error), video_id)
    except Exception as error:
        return _transcript_error(_safe_transcript_error(error), video_id)


def _transcript_error(message: str, video_id: str | None = None) -> dict:
    return {
        "status": "error",
        "error": message,
        "transcript": message,
        "segments": [],
        "video_id": video_id,
        "title": None,
        "thumbnail": None,
    }


def _safe_transcript_error(error: Exception) -> str:
    name = type(error).__name__
    message = str(error).lower()
    if "429" in message or name == "TooManyRequests":
        return "YouTube rate-limited transcript retrieval. Please retry later."
    if name in {"VideoUnavailable", "InvalidVideoId"}:
        return "The YouTube video is unavailable or invalid."
    return "Transcript retrieval failed. The video may be restricted or temporarily unavailable."


def manual_transcript_data(transcript: str, video_url: str = "") -> dict:
    """Convert pasted plain text or timestamped transcript text to app cues."""
    cleaned_lines = []
    segments = []
    timestamp_pattern = re.compile(
        r"^\s*(?:\[)?(?P<minutes>\d{1,3}):(?P<seconds>\d{2})(?:\])?\s+(?P<text>.+?)\s*$"
    )

    for line in transcript.splitlines():
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line:
            continue
        match = timestamp_pattern.match(line)
        if match:
            start = int(match.group("minutes")) * 60 + int(match.group("seconds"))
            text = re.sub(r"\s+", " ", match.group("text")).strip()
            segments.append({"start": float(start), "end": float(start), "text": text})
            cleaned_lines.append(text)
        else:
            cleaned_lines.append(re.sub(r"\s+", " ", line))

    cleaned_transcript = " ".join(cleaned_lines).strip()
    if not cleaned_transcript:
        return _transcript_error("The transcript is empty.")

    if segments:
        for index, segment in enumerate(segments):
            next_start = segments[index + 1]["start"] if index + 1 < len(segments) else segment["start"]
            segment["end"] = max(segment["start"], float(next_start))

    return {
        "status": "ok",
        "transcript": cleaned_transcript,
        "segments": segments,
        "video_id": extract_video_id(video_url) if video_url else None,
        "title": None,
        "thumbnail": None,
    }


def fetch_transcript(video_url: str) -> str:
    """
    Fetch transcript (manual or automatic subtitles) for a given YouTube video.
    Returns the transcript as clean text, or an error message if unavailable.
    Tries multiple fallback strategies to handle geo-blocked or restricted videos.
    """
    transcript_data = fetch_transcript_data(video_url)
    return transcript_data.get("transcript", "Transcript is empty.")

def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    segments: list[dict] | None = None,
) -> list:
    """
    Splits text into chunks for embedding.

    If `segments` (timestamped cues) are provided, chunking will be done by grouping
    adjacent segments so that each chunk is roughly `chunk_size` characters and
    each returned item is a dict: {"text": ..., "start": float, "end": float}.

    If `segments` is None, falls back to the original character-based chunking and
    returns a list of strings for backwards compatibility.
    """
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0:
        raise ValueError("overlap cannot be negative.")
    # An overlap equal to the whole chunk would never advance the cursor.
    overlap = min(overlap, chunk_size - 1)

    if segments:
        # Chunk by segments and attach timestamp metadata to each chunk.
        chunks: list[dict] = []
        n = len(segments)
        idx = 0
        while idx < n:
            char_count = 0
            start_idx = idx
            start_time = segments[start_idx].get("start")
            end_time = start_time
            texts: list[str] = []
            # accumulate segments until chunk_size reached
            while idx < n:
                seg_text = segments[idx].get("text", "")
                seg_len = len(seg_text)
                if char_count > 0 and char_count + seg_len > chunk_size:
                    break
                texts.append(seg_text)
                char_count += seg_len
                end_time = segments[idx].get("end", end_time)
                idx += 1

            # if a single segment is larger than chunk_size, we still include it
            if not texts and start_idx < n:
                seg = segments[start_idx]
                chunks.append({"text": seg.get("text", ""), "start": seg.get("start"), "end": seg.get("end")})
                idx = start_idx + 1
                continue

            chunk_text = " ".join(t for t in texts if t).strip()
            if chunk_text:
                chunks.append({"text": chunk_text, "start": float(start_time), "end": float(end_time)})

            # implement a simple overlap by moving idx back to include previous segments
            if overlap and chunks:
                # compute overlap in characters and step back accordingly
                back_chars = 0
                back_idx = idx - 1
                while back_idx >= 0 and back_chars < overlap:
                    back_chars += len(segments[back_idx].get("text", ""))
                    back_idx -= 1
                # next start is back_idx + 1, but ensure progress
                idx = max(back_idx + 1, start_idx + 1)

        return chunks

    # fallback: original character-based splitting
    chunks: list[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        # Advance by chunk_size minus overlap.  The old max(...) expression
        # always selected ``end``, silently disabling overlap.
        start = end - overlap
    return chunks
