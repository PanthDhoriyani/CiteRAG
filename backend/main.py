from fastapi import FastAPI
from routers import upload, query

app = FastAPI(
    title="Citation-Aware Multi-Source RAG Platform",
    description="Backend API for document ingestion, retrieval, and analysis",
    version="0.1.0"
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(query.router, prefix="/api", tags=["query"])

@app.get("/")
async def root():
    return {"message": "Welcome to the RAG Platform API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}