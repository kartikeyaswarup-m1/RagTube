import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes import ingest, query
from backend.app.routes import diagnostics

app = FastAPI(title="RagTube Backend")

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router,  prefix="/query",  tags=["query"])
app.include_router(diagnostics.router, prefix="/diagnostics", tags=["diagnostics"])

@app.get("/")
def root():
    return {"message": "Welcome to RagTube Backend 🚀"}