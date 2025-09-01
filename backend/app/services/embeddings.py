import os
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")  # make sure you pulled this: ollama pull nomic-embed-text

def get_embedding(text: str):
    """
    Generate embeddings for text using Ollama embedding models.
    """
    url = f"{OLLAMA_HOST}/api/embeddings"
    payload = {
        "model": EMBED_MODEL,
        "prompt": text
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("embedding", [])
    except Exception as e:
        raise RuntimeError(f"Error generating embeddings: {e}")