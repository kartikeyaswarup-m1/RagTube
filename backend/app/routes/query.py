from fastapi import APIRouter, Query
import ollama

router = APIRouter()

@router.get("/query")
async def query_llm(question: str = Query(..., description="Your question")):
    """
    Query the Ollama LLM with a user question.
    """
    try:
        # Send the prompt to Ollama
        response = ollama.chat(
            model="llama2",  # change this to the model you have pulled, e.g. "mistral", "gemma", etc.
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ]
        )
        answer = response["message"]["content"]

        return {"question": question, "answer": answer}

    except Exception as e:
        return {"error": str(e)}