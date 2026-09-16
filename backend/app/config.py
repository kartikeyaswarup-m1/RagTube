# backend/app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def _env(name: str, default: str = "") -> str:
	return os.getenv(name, default).strip()


VECTORSTORE_DIR = Path(_env("VECTORSTORE_DIR", str(BASE_DIR / "vectorstore"))).expanduser()
LLM_PROVIDER = _env("LLM_PROVIDER", "groq").lower()
GROQ_MODEL = _env("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = _env("GROQ_API_KEY")

# Ensure vectorstore dir exists
VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

# Hugging Face settings
HF_API_TOKEN = _env("HF_API_TOKEN")
HF_MODEL = _env("HF_MODEL", "gpt2")
HF_EMBED_MODEL = _env("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_PROVIDER = _env("EMBED_PROVIDER", "hf").lower()

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
	origin
	for origin in _env("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
	if origin
]


def missing_runtime_configuration() -> list[str]:
	"""Return names of credentials needed for the configured providers."""
	missing = []
	if LLM_PROVIDER == "groq" and not GROQ_API_KEY:
		missing.append("GROQ_API_KEY")
	if EMBED_PROVIDER == "hf" and not HF_API_TOKEN:
		missing.append("HF_API_TOKEN")
	return missing