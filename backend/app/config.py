# backend/app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

VECTORSTORE_DIR = Path(os.getenv("VECTORSTORE_DIR", BASE_DIR / "vectorstore"))
# Ollama removed — default to Groq for cloud deployments
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "<REDACTED_GROQ_API_KEY>").strip()

# Ensure vectorstore dir exists
VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

# Hugging Face / alternative cloud provider settings
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "").strip()
HF_MODEL = os.getenv("HF_MODEL", "gpt2")
HF_EMBED_MODEL = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "").strip().lower()