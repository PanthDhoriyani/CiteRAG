from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
import logging

from .routers import upload, query

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Citation-Aware Multi-Source RAG Platform",
    description="Backend API for document ingestion, retrieval, and analysis",
    version="0.1.0"
)

# CORS middleware — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(query.router, prefix="/api", tags=["query"])

# Serve frontend static files if the frontend directory exists
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

@app.get("/")
async def root():
    """Redirect root to the frontend UI."""
    return RedirectResponse(url="/frontend/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint with optional service status."""
    status = {"status": "healthy", "api": True}

    # Check database connections (non-blocking, best-effort)
    try:
        from .db.elastic_client import ElasticSearchDB
        es = ElasticSearchDB()
        status["elasticsearch"] = es.health_check()
    except Exception:
        status["elasticsearch"] = False

    try:
        from .db.mongo_client import MongoDB
        mongo = MongoDB()
        status["mongodb"] = mongo.health_check()
    except Exception:
        status["mongodb"] = False

    try:
        from .db.qdrant_client import QdrantDB
        qdrant = QdrantDB()
        status["qdrant"] = qdrant.health_check()
    except Exception:
        status["qdrant"] = False

    # Overall status
    all_healthy = all([
        status.get("elasticsearch", False),
        status.get("mongodb", False),
        status.get("qdrant", False),
    ])
    status["status"] = "healthy" if all_healthy else "degraded"

    return status