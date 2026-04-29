import os
import faiss
import numpy as np
import pickle
from pathlib import Path
from .embeddings import get_embedding
from backend.app.config import VECTORSTORE_DIR  # <-- changed

INDEX_FILE = VECTORSTORE_DIR / "faiss.index"
MAPPING_FILE = VECTORSTORE_DIR / "mapping.pkl"

# ensure directory exists
VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

def save_vectorstore(texts: list[str]):
    """
    Build FAISS index for given texts and persist it to disk.
    """
    if not texts:
        raise ValueError("No texts provided to save_vectorstore.")
    # texts may be a list of strings or a list of dicts with a 'text' key.
    embeddings = [get_embedding(t["text"] if isinstance(t, dict) else t) for t in texts]
    dim = len(embeddings[0])

    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings, dtype="float32"))

    # persist the original items (strings or dicts) so we can return metadata later
    with open(MAPPING_FILE, "wb") as f:
        pickle.dump(texts, f)

    faiss.write_index(index, str(INDEX_FILE))

def query_vectorstore(query: str, top_k: int = 3):
    """
    Search FAISS index with query and return top matching texts.
    """
    if not INDEX_FILE.exists() or not MAPPING_FILE.exists():
        raise RuntimeError("Vectorstore not built yet. Please ingest a video first.")

    index = faiss.read_index(str(INDEX_FILE))
    with open(MAPPING_FILE, "rb") as f:
        texts = pickle.load(f)

    query_vec = np.array([get_embedding(query)], dtype="float32")
    distances, indices = index.search(query_vec, top_k)

    results = []
    for i in indices[0]:
        if 0 <= i < len(texts):
            results.append(texts[i])
    return results