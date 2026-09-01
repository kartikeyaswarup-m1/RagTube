from fastapi import APIRouter
import socket
import requests
from backend.app.config import HF_API_TOKEN, EMBED_PROVIDER, GROQ_API_KEY

router = APIRouter()


@router.get("")
def diagnostics():
    """Run basic DNS and HTTP connectivity checks from the running process.

    This is safe to expose temporarily on a deployed service to debug
    network/DNS/egress issues when a shell is not available.
    """
    result = {
        "env": {
            "embed_provider_set": bool(EMBED_PROVIDER),
            "hf_token_present": bool(HF_API_TOKEN),
            "groq_key_present": bool(GROQ_API_KEY),
        },
        "checks": {},
    }

    host = "api-inference.huggingface.co"
    # DNS resolution
    try:
        infos = socket.getaddrinfo(host, 443)
        addrs = sorted({f"{ai[4][0]}:{ai[4][1]}" for ai in infos})
        result["checks"]["dns"] = {"ok": True, "addresses": addrs}
    except Exception as e:
        result["checks"]["dns"] = {"ok": False, "error": str(e)}

    # HTTP reachability (HEAD/GET)
    try:
        url = "https://api-inference.huggingface.co/embeddings"
        # do a lightweight request; token may be missing/invalid (that's OK)
        resp = requests.post(url, json={"model": "test", "input": "ping"}, timeout=10)
        result["checks"]["http"] = {"ok": True, "status_code": resp.status_code, "reason": resp.reason}
    except Exception as e:
        result["checks"]["http"] = {"ok": False, "error": str(e)}

    return result
