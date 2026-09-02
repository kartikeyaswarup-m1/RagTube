import os
import logging
import requests

from backend.app.config import (
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
    provider = (EMBED_PROVIDER or LLM_PROVIDER or "hf").strip().lower()

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
            # If enabled, return a deterministic dev fallback embedding so the
            # app remains usable while network/keys are being fixed.
            logging.warning("HF embedding error: %s", e)
            enable_fallback = os.getenv("ENABLE_EMBED_FALLBACK", "").strip().lower() in ("1", "true", "yes")
            if enable_fallback:
                # Default to 384-dimensional zero vector (miniLM default)
                return [0.0] * 384
            raise RuntimeError(f"Error generating embeddings from Hugging Face: {e}")

    raise RuntimeError(f"No supported embedding provider configured. Set EMBED_PROVIDER=hf or provide HF_API_TOKEN.")