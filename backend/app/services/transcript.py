import json
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
import yt_dlp


def _normalize_youtube_url(video_url: str) -> str:
    """Strip playlist-specific parameters so yt_dlp treats the URL as a single video.

    Some YouTube share links include `list` and `index` query params. Those can make
    yt_dlp lean toward playlist handling, which is unnecessary for transcript ingest.
    """
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

    normalized_query = urlencode({"v": video_id})
    return urlunparse(("https", "www.youtube.com", "/watch", "", normalized_query, ""))


def _timestamp_to_seconds(timestamp: str) -> float:
    parts = timestamp.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"Unsupported timestamp format: {timestamp}")

    return (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)


def _clean_caption_text(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _parse_vtt_cues(raw_text: str) -> list[dict]:
    cues: list[dict] = []
    lines = [line.rstrip("\n") for line in raw_text.splitlines()]
    index = 0

    while index < len(lines):
        line = lines[index].strip()

        if not line or line == "WEBVTT" or line.startswith(("NOTE", "STYLE")):
            index += 1
            continue

        if "-->" not in line:
            if index + 1 < len(lines) and "-->" in lines[index + 1]:
                index += 1
                line = lines[index].strip()
            else:
                index += 1
                continue

        match = re.match(
            r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})",
            line,
        )
        if not match:
            index += 1
            continue

        index += 1
        text_lines: list[str] = []
        while index < len(lines):
            text_line = lines[index].strip()
            if not text_line:
                break
            if text_line.startswith(("NOTE", "STYLE")):
                break
            text_lines.append(text_line)
            index += 1

        text = _clean_caption_text(" ".join(text_lines))
        if text:
            cues.append(
                {
                    "start": _timestamp_to_seconds(match.group("start")),
                    "end": _timestamp_to_seconds(match.group("end")),
                    "text": text,
                }
            )

        while index < len(lines) and not lines[index].strip():
            index += 1

    return cues


def _parse_json_cues(raw_text: str) -> list[dict]:
    data = json.loads(raw_text)
    cues: list[dict] = []

    for event in data.get("events", []):
        segments = event.get("segs", [])
        text = _clean_caption_text("".join(segment.get("utf8", "") for segment in segments))
        start_ms = event.get("tStartMs")
        if not text or start_ms is None:
            continue

        duration_ms = event.get("dDurationMs")
        start = float(start_ms) / 1000.0
        end = start + (float(duration_ms) / 1000.0 if duration_ms else 0.0)
        cues.append({"start": start, "end": end, "text": text})

    return cues


def _select_caption_track(tracks: dict) -> list[dict]:
    if not tracks:
        return []

    for language_code in ("en", "en-US", "en-GB"):
        if language_code in tracks:
            return tracks[language_code]

    for language_code, track_list in tracks.items():
        if language_code.lower().startswith("en"):
            return track_list

    return next(iter(tracks.values()), [])


def _parse_caption_cues(raw_text: str) -> list[dict]:
    if raw_text.strip().startswith("{"):
        try:
            return _parse_json_cues(raw_text)
        except Exception:
            return []

    return _parse_vtt_cues(raw_text)


def fetch_transcript_data(video_url: str) -> dict:
    """
    Fetch transcript metadata and timestamped cues for a given YouTube video.
    Returns a dictionary with transcript text, cue data, and video metadata.
    """
    ydl_opts = {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "skip_download": True,
        "subtitleslangs": ["en"],
        "quiet": True,
        "no_warnings": True,
        "ignore_no_formats_error": True,
        "noplaylist": True,
    }

    try:
        normalized_url = _normalize_youtube_url(video_url)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(normalized_url, download=False)

            subtitles = info.get("subtitles", {})
            if not subtitles or not _select_caption_track(subtitles):
                subtitles = info.get("automatic_captions", {})

            caption_tracks = _select_caption_track(subtitles)
            if not caption_tracks:
                return {
                    "status": "failed",
                    "error": "No transcript available for this video.",
                    "transcript": "No transcript available for this video.",
                    "segments": [],
                    "video_id": info.get("id"),
                    "title": info.get("title"),
                    "thumbnail": info.get("thumbnail"),
                }

            subtitle_url = caption_tracks[0]["url"]
            response = requests.get(subtitle_url, timeout=10)
            if response.status_code != 200:
                return {
                    "status": "failed",
                    "error": "Failed to fetch transcript.",
                    "transcript": "Failed to fetch transcript.",
                    "segments": [],
                    "video_id": info.get("id"),
                    "title": info.get("title"),
                    "thumbnail": info.get("thumbnail"),
                }

            segments = _parse_caption_cues(response.text)
            transcript = " ".join(segment["text"] for segment in segments).strip()

            if not transcript:
                transcript = "Transcript is empty."

            return {
                "status": "ok",
                "transcript": transcript,
                "segments": segments,
                "video_id": info.get("id"),
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
            }

    except Exception as e:
        error_str = str(e)
        if "Requested format is not available" in error_str:
            error_message = "Error: Video format unavailable. Try a different video or check if it's geo-blocked."
        elif "age-restricted" in error_str or "429" in error_str:
            error_message = "Error: Video is age-restricted or temporarily unavailable."
        elif "video not found" in error_str or "unavailable" in error_str:
            error_message = "Error: Video not found or unavailable."
        else:
            error_message = f"Error fetching transcript: {error_str}"

        return {
            "status": "error",
            "error": error_message,
            "transcript": error_message,
            "segments": [],
            "video_id": None,
            "title": None,
            "thumbnail": None,
        }

def fetch_transcript(video_url: str) -> str:
    """
    Fetch transcript (manual or automatic subtitles) for a given YouTube video using yt_dlp.
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
        start = max(end - overlap, end)
    return chunks
