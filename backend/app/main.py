# backend/app/main.py
from fastapi import FastAPI
from backend.app.routes import ingest, query

app = FastAPI(title="RagTube Backend")

# Include routes
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router, prefix="/query", tags=["query"])

@app.get("/")
def root():
    return {"message": "Welcome to RagTube Backend 🚀"}