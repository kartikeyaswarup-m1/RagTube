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
import json

from backend.app.services.retriever import query_vectorstore
from backend.app.services.llm import stream_response

router = APIRouter()


@router.get("")
async def query_llm(
    question: str = Query(..., description="Your question"),
    provider: str = Query("ollama", description="LLM provider: ollama or groq"),
):
    """Stream LLM output as newline-delimited JSON (NDJSON).

    Client should consume line-by-line JSON objects with keys `text` or `error`.
    """

    def generate():
        try:
            # Step 1 – retrieve relevant text chunks
            contexts = query_vectorstore(question, top_k=4)

            def _format_ts(seconds: float) -> str:
                if seconds is None:
                    return "00:00"
                s = int(seconds)
                hours = s // 3600
                minutes = (s % 3600) // 60
                secs = s % 60
                if hours:
                    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
                return f"{minutes:02d}:{secs:02d}"

            # Step 2 – build a combined prompt
            # Build context text with timestamp markers when available.
            formatted_contexts = []
            references = []
            for i, ctx in enumerate(contexts, start=1):
                if isinstance(ctx, dict):
                    start = ctx.get("start")
                    end = ctx.get("end")
                    text = ctx.get("text", "")
                    ts = _format_ts(start)
                    formatted_contexts.append(f"[{ts}] {text}")
                    references.append({"label": f"[{ts}]", "start": start, "end": end, "text": text})
                else:
                    # plain string fallback
                    formatted_contexts.append(str(ctx))

            context_text = "\n\n".join(formatted_contexts)

            prompt = (
                "You are a helpful, detailed assistant answering questions about a YouTube video. "
                "Use the provided transcript excerpts (marked with timestamps) to craft a thorough, multi-paragraph answer. "
                "Format the response in clean markdown: use short headings, bold labels, and bullet points when helpful. "
                "When you cite specific facts, include an inline timestamp citation in square brackets, e.g. [00:43]. "
                "At the end of your answer, include a short 'References' section that lists each timestamp you relied on and the excerpt text. "
                "Keep the tone clear and readable, and avoid dumping the transcript verbatim.\n\n"
                f"Context:\n{context_text}\n\n"
                f"Question: {question}\n\n"
                f"Answer:"
            )

            # Step 3 – ask the selected LLM provider with streaming
            for text in stream_response(prompt, provider=provider):
                if text:
                    yield json.dumps({"text": text}) + "\n"

            # Final marker
            yield json.dumps({"done": True}) + "\n"

        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
