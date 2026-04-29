import requests

from backend.app.config import EMBED_MODEL, OLLAMA_HOST

def get_embedding(text: str):
    """
    Generate embeddings for text using Ollama embedding models.
    NOTE: /api/embeddings expects 'input', not 'prompt'.
    """
    url = f"{OLLAMA_HOST}/api/embeddings"
    payload = {
        "model": EMBED_MODEL,
        "input": text
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("embedding", [])
    except Exception as e:
            raise RuntimeError(f"Error generating embeddings from {OLLAMA_HOST} using {EMBED_MODEL}: {e}")