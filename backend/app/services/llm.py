import json
from typing import Iterator

import requests
from groq import Groq

from backend.app.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_PROVIDER,
    OLLAMA_HOST,
    OLLAMA_MODEL,
)


def _normalize_provider(provider: str | None) -> str:
    return (provider or LLM_PROVIDER or "ollama").strip().lower()


def _stream_ollama(prompt: str, model: str | None = None) -> Iterator[str]:
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "temperature": 0.4,  # Lower temp for more focused, accurate answers
        "top_p": 0.85,  # Control diversity without being too restrictive
        "top_k": 40,  # Limit token pool for consistency
    }

    response = requests.post(url, json=payload, stream=True, timeout=120)
    response.raise_for_status()

    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue

        # Ensure line is a string (sometimes iter_lines returns bytes)
        if isinstance(line, bytes):
            line = line.decode("utf-8")

        if line.startswith("data: "):
            line = line.removeprefix("data: ").strip()

        if not line:
            continue

        try:
            payload = json.loads(line)
        except Exception:
            continue

        chunk = payload.get("response", "")
        if chunk:
            yield chunk


def _stream_groq(prompt: str, model: str | None = None) -> Iterator[str]:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set.")

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=model or GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful video assistant."},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )

    for chunk in response:
        try:
            choice = chunk.choices[0]
            delta = getattr(choice, "delta", None)
            text = getattr(delta, "content", None) if delta is not None else None
            if text:
                yield text
        except Exception:
            continue


def generate_response(prompt: str, provider: str | None = None, model: str | None = None) -> str:
    """
    Sends a prompt to the configured provider and returns the generated response.
    """
    try:
        return "".join(stream_response(prompt, provider=provider, model=model)).strip()
    except Exception as e:
        return f"Error calling LLM provider: {e}"


def stream_response(prompt: str, provider: str | None = None, model: str | None = None) -> Iterator[str]:
    """
    Stream text chunks from Ollama or Groq.
    """
    selected_provider = _normalize_provider(provider)

    if selected_provider == "groq":
        yield from _stream_groq(prompt, model=model)
        return

    if selected_provider != "ollama":
        raise ValueError(f"Unsupported provider: {selected_provider}")

    yield from _stream_ollama(prompt, model=model)