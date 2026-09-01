import requests

from backend.app.config import (
    EMBED_MODEL,
    OLLAMA_HOST,
    HF_API_TOKEN,
    HF_EMBED_MODEL,
    EMBED_PROVIDER,
    LLM_PROVIDER,
)


def get_embedding(text: str):
    """
    Generate embeddings for text using Ollama or Hugging Face.
    Prefers provider specified by `EMBED_PROVIDER`; falls back to `LLM_PROVIDER`.
    """
    provider = (EMBED_PROVIDER or LLM_PROVIDER or "ollama").strip().lower()

    if provider == "hf":
        if not HF_API_TOKEN:
            raise RuntimeError("HF_API_TOKEN is not set for Hugging Face embeddings")

        url = "https://api-inference.huggingface.co/embeddings"
        headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
        payload = {"model": HF_EMBED_MODEL, "input": text}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            # Response might be {'embedding': [...] } or list/array directly
            if isinstance(data, dict) and "embedding" in data:
                return data["embedding"]
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], (int, float)):
                return data
            # Some endpoints return nested lists (per-token); try flatten/average
            if isinstance(data, list) and all(isinstance(i, list) for i in data):
                # average across token vectors
                import numpy as _np

                arr = _np.array(data, dtype=float)
                return _np.mean(arr, axis=0).tolist()

            raise RuntimeError(f"Unexpected embeddings response from Hugging Face: {data}")

        except Exception as e:
            raise RuntimeError(f"Error generating embeddings from Hugging Face: {e}")

    # Default: Ollama
    url = f"{OLLAMA_HOST}/api/embeddings"
    payload = {
        "model": EMBED_MODEL,
        "input": text,
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("embedding", [])
    except Exception as e:
        raise RuntimeError(f"Error generating embeddings from {OLLAMA_HOST} using {EMBED_MODEL}: {e}")