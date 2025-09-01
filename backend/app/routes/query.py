from fastapi import APIRouter, Query
import os
import ollama  # pip install ollama

router = APIRouter()

# NOTE: no '/query' here; main.py already prefixes this router with '/query'
@router.get("")
async def query_llm(question: str = Query(..., description="Your question")):
    try:
        model = os.getenv("OLLAMA_MODEL", "llama3")
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ]
        )
        answer = response["message"]["content"]
        return {"question": question, "answer": answer}
    except Exception as e:
        return {"error": str(e)}