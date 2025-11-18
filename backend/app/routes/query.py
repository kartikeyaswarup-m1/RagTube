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
from fastapi.responses import StreamingResponse
import os, ollama, json
from backend.app.services.retriever import query_vectorstore

router = APIRouter()


@router.get("")
async def query_llm(question: str = Query(..., description="Your question")):
    """Stream LLM output as newline-delimited JSON (NDJSON).

    Client should consume line-by-line JSON objects with keys `text` or `error`.
    """

    def generate():
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

            # Step 3 – ask the LLM with streaming
            model = os.getenv("OLLAMA_MODEL", "llama3")
            # ask ollama for a streaming response
            response_iter = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful video assistant."},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )

            # Iterate over the streaming response and yield ndjson lines
            for chunk in response_iter:
                try:
                    text = ""
                    # Extract text from chunk object
                    if hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                        text = chunk.message.content
                    elif isinstance(chunk, dict):
                        if "message" in chunk and isinstance(chunk["message"], dict):
                            text = chunk["message"].get("content", "")
                        else:
                            text = chunk.get("content", "") or chunk.get("text", "")
                    
                    if text:
                        yield json.dumps({"text": text}) + "\n"
                except Exception:
                    continue

            # Final marker
            yield json.dumps({"done": True}) + "\n"

        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
