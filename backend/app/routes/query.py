# from fastapi import APIRouter, Query
# import os
# import ollama  # pip install ollama

# router = APIRouter()

# # NOTE: no '/query' here; main.py already prefixes this router with '/query'
# @router.get("")
# async def query_llm(question: str = Query(..., description="Your question")):
#     try:
#         model = os.getenv("OLLAMA_MODEL", "llama3")
#         response = ollama.chat(
#             model=model,
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant."},
#                 {"role": "user", "content": question},
#             ]
#         )
#         answer = response["message"]["content"]
#         return {"question": question, "answer": answer}
#     except Exception as e:
#         return {"error": str(e)}

from fastapi import APIRouter, Query
import os, ollama
from backend.app.services.retriever import query_vectorstore

router = APIRouter()

@router.get("")
async def query_llm(question: str = Query(..., description="Your question")):
    try:
        # Step 1 – retrieve relevant text chunks
        contexts = query_vectorstore(question, top_k=3)

        # Step 2 – build a combined prompt
        context_text = "\n\n".join(contexts)
        prompt = (
            f"Use the following transcript excerpts to answer the question.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {question}\n"
            f"Answer:"
        )

        # Step 3 – ask the LLM
        model = os.getenv("OLLAMA_MODEL", "phi3")
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful video assistant."},
                {"role": "user", "content": prompt},
            ],
        )

        answer = response["message"]["content"]
        return {"question": question, "answer": answer}

    except Exception as e:
        return {"error": str(e)}
