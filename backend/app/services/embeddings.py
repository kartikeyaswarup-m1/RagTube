import os
import logging
from collections.abc import Sequence

from huggingface_hub import InferenceClient

from backend.app.config import (
    HF_API_TOKEN,
    HF_EMBED_MODEL,
    EMBED_PROVIDER,
)


class EmbeddingError(RuntimeError):
    """A safe, user-facing embedding provider failure."""


def _embedding_values(result) -> list[float]:
    """Normalize InferenceClient output to one flat embedding vector."""
    if hasattr(result, "tolist"):
        result = result.tolist()

    if isinstance(result, Sequence) and not isinstance(result, (str, bytes)):
        values = list(result)
        if values and isinstance(values[0], Sequence):
            rows = [[float(value) for value in row] for row in values]
            width = len(rows[0])
            if not width or any(len(row) != width for row in rows):
                raise EmbeddingError("Hugging Face returned an invalid embedding shape")
            return [sum(row[index] for row in rows) / len(rows) for index in range(width)]
        if values and all(isinstance(value, (int, float)) for value in values):
            return [float(value) for value in values]

    raise EmbeddingError("Hugging Face returned an invalid embedding response")


def get_embedding(text: str):
    """
    Generate embeddings through Hugging Face's supported InferenceClient API.
    """
    provider = (EMBED_PROVIDER or "hf").strip().lower()

    if provider == "hf":
        if not HF_API_TOKEN:
            raise EmbeddingError("HF_API_TOKEN is not set for Hugging Face embeddings")

        try:
            client = InferenceClient(provider="hf-inference", token=HF_API_TOKEN, timeout=60)
            result = client.feature_extraction(text, model=HF_EMBED_MODEL)
            return _embedding_values(result)
        except EmbeddingError:
            raise
        except Exception as e:
            # If enabled, return a deterministic dev fallback embedding so the
            # app remains usable while network/keys are being fixed.
            logging.warning("Hugging Face embedding request failed: %s", type(e).__name__)
            enable_fallback = os.getenv("ENABLE_EMBED_FALLBACK", "").strip().lower() in ("1", "true", "yes")
            if enable_fallback:
                # Default to 384-dimensional zero vector (miniLM default)
                return [0.0] * 384
            raise EmbeddingError(
                "Hugging Face embedding request failed. Check HF_API_TOKEN, HF_EMBED_MODEL, "
                "and outbound network access."
            ) from e

    raise EmbeddingError("Unsupported EMBED_PROVIDER. Set EMBED_PROVIDER=hf.")