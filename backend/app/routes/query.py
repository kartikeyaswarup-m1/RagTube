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
                "You are an expert assistant answering questions about a YouTube video based on its transcript.\n\n"
                "INSTRUCTIONS:\n"
                "1. Use ONLY the provided transcript excerpts to answer. If information is not in the transcript, say so.\n"
                "2. Provide a clear, well-structured answer with:\n"
                "   - A brief direct answer to the main question\n"
                "   - Key supporting details from the transcript\n"
                "   - Concrete examples or points when relevant\n"
                "3. Format your response:\n"
                "   - Use **bold** for key terms or speaker names\n"
                "   - Use bullet points for lists\n"
                "   - Use short headings (## format) for sections if needed\n"
                "4. Cite timestamps inline [MM:SS] whenever you reference a specific moment or quote.\n"
                "5. Be concise but thorough—aim for 2-4 paragraphs unless more detail is truly needed.\n"
                "6. Keep tone professional, informative, and accessible.\n\n"
                f"TRANSCRIPT CONTEXT:\n{context_text}\n\n"
                f"QUESTION: {question}\n\n"
                f"ANSWER:"
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
