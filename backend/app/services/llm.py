import json
from typing import Iterator

import requests
from groq import Groq

from backend.app.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_PROVIDER,
    HF_API_TOKEN,
    HF_MODEL,
)


def _normalize_provider(provider: str | None) -> str:
    return (provider or LLM_PROVIDER or "groq").strip().lower()


# Ollama support removed. Groq remains the primary streaming provider.


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


def _stream_hf(prompt: str, model: str | None = None) -> Iterator[str]:
    """
    Simple (non-streaming) huggingface inference call wrapped as an iterator.
    Falls back to returning the whole response as one chunk.
    """
    if not HF_API_TOKEN:
        raise RuntimeError("HF_API_TOKEN is not set.")

    chosen = model or HF_MODEL
    url = f"https://api-inference.huggingface.co/models/{chosen}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": prompt,
        "options": {"wait_for_model": True},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"Error calling Hugging Face Inference API: {e}")

    # Attempt to extract generated text from common response shapes
    out = ""
    if isinstance(data, dict) and "generated_text" in data:
        out = data["generated_text"]
    elif isinstance(data, list) and len(data) > 0:
        first = data[0]
        if isinstance(first, dict) and "generated_text" in first:
            out = first["generated_text"]
        else:
            # Many models return a list of tokens/strings
            out = " ".join(map(str, data))
    else:
        out = str(data)

    if out:
        yield out


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
    Stream text chunks from Groq or Hugging Face.
    """
    selected_provider = _normalize_provider(provider)

    if selected_provider == "groq":
        yield from _stream_groq(prompt, model=model)
        return

    if selected_provider == "hf":
        yield from _stream_hf(prompt, model=model)
        return
    raise ValueError(f"Unsupported provider: {selected_provider}")