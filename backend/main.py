from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import logging

from .routers import upload, query, documents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs startup logic, then yields for the app to run."""
    logger.info("=" * 60)
    logger.info("CiteRAG backend starting up")
    logger.info("  API docs  : http://localhost:8000/docs")
    logger.info("  Frontend  : http://localhost:8000/frontend/index.html")
    logger.info("  Health    : http://localhost:8000/health")
    logger.info("Tip: run 'docker-compose up -d' to start Qdrant, MongoDB, Elasticsearch & Ollama")
    logger.info("=" * 60)
    yield  # Application runs here
    logger.info("CiteRAG backend shutting down")


app = FastAPI(
    title="CiteRAG — Citation-Aware Multi-Source RAG Platform",
    description="Backend API for document ingestion, hybrid retrieval, and analysis",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware — allow the frontend (served or opened directly) to talk to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(documents.router, prefix="/api", tags=["documents"])

# Serve frontend static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    logger.info(f"Frontend served from {frontend_dir}")





@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to the frontend UI."""
    return RedirectResponse(url="/frontend/index.html")


@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint.
    All service checks run concurrently so the endpoint responds in
    max(individual_timeout) seconds rather than sum(all_timeouts).
    """
    loop = asyncio.get_running_loop()

    def _check_es():
        try:
            from .db.elastic_client import ElasticSearchDB
            return ElasticSearchDB().health_check()
        except Exception:
            return False

    def _check_mongo():
        try:
            from .db.mongo_client import MongoDB
            return MongoDB().health_check()
        except Exception:
            return False

    def _check_qdrant():
        try:
            from .db.qdrant_client import QdrantDB
            return QdrantDB().health_check()
        except Exception:
            return False

    def _check_ollama():
        try:
            import requests as _req
            from .config import config
            r = _req.get(
                f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}/api/tags",
                timeout=2,
            )
            return r.status_code == 200
        except Exception:
            return False

    # Run all checks concurrently — total latency ≈ slowest single check
    es_ok, mongo_ok, qdrant_ok, ollama_ok = await asyncio.gather(
        loop.run_in_executor(None, _check_es),
        loop.run_in_executor(None, _check_mongo),
        loop.run_in_executor(None, _check_qdrant),
        loop.run_in_executor(None, _check_ollama),
    )

    status: dict = {
        "status": "healthy",
        "api": True,
        "elasticsearch": es_ok,
        "mongodb": mongo_ok,
        "qdrant": qdrant_ok,
        "ollama": ollama_ok,
    }

    core_healthy = es_ok and mongo_ok and qdrant_ok
    status["status"] = "healthy" if core_healthy else "degraded"

    down = [k for k, v in status.items() if k not in ("status", "api") and v is False]
    if down:
        status["hint"] = (
            f"The following services are down: {', '.join(down)}. "
            "Run: docker-compose up -d"
        )

    return status