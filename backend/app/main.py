from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes import ingest, query
from backend.app.routes import diagnostics
from backend.app.config import CORS_ORIGINS, missing_runtime_configuration

app = FastAPI(title="RagTube Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router,  prefix="/query",  tags=["query"])
app.include_router(diagnostics.router, prefix="/diagnostics", tags=["diagnostics"])

@app.get("/")
def root():
    return {"message": "Welcome to RagTube Backend"}


@app.get("/health")
def health():
    missing = missing_runtime_configuration()
    return {
        "status": "ok" if not missing else "degraded",
        "configuration": {
            "missing": missing,
        },
    }