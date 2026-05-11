# Memory Log

- 2026-05-09: Set up FastAPI project structure and basic file upload endpoint (Task #1 completed). Created backend/, routers/, main.py, upload router with file validation and storage.
- 2026-05-09: Created extractor service (backend/services/extractor.py) with multi-method text extraction: PyMuPDF (primary), pdfplumber (fallback), Tesseract OCR (scanned PDFs), python-docx (DOCX), plain read (TXT).
- 2026-05-09: Created chunker service (backend/services/chunker.py) using LangChain's RecursiveCharacterTextSplitter with configurable chunk size (512) and overlap (128). Includes functions for plain chunking and chunking with metadata attachment.
- 2026-05-09: Created embedder service (backend/services/embedder.py) using sentence-transformers BAAI/bge-large-en-v1.5 model. Provides functions to embed lists of texts and single queries, returning numpy arrays.
- 2026-05-09: Created database clients:
  • Qdrant (backend/db/qdrant_client.py) for vector storage with collection management and search.
  • MongoDB (backend/db/mongo_client.py) for metadata and raw text storage.
  • Elasticsearch (backend/db/elastic_client.py) for BM25 keyword search.
- 2026-05-09: Created processor service (backend/services/processor.py) that orchestrates the full pipeline: extraction → chunking → embedding → storage in all three databases (Qdrant, MongoDB, Elasticsearch).
- 2026-05-09: Updated upload router (backend/routers/upload.py) to call the processor after saving the file, enabling end-to-end ingestion: upload → text extraction → chunking → embedding → storage in Qdrant, MongoDB, and Elasticsearch.
- 2026-05-09: Task #2 completed: Implemented text extraction, chunking, embedding, and storage systems. All services are integrated and the upload endpoint returns processing results.
- 2026-05-09: Created flow.md (root) explaining the project directory structure, file purposes, and data flow for backend (Phase 1 only). Updated to reflect only implemented files/folders.
- 2026-05-10: Improved configuration management and database connectivity:
  • Created centralized configuration module (backend/config.py) using environment variables with .env file support
  • Updated all database clients (qdrant_client.py, mongo_client.py, elastic_client.py) to:
    - Accept optional connection parameters with fallback to configuration values
    - Add connection health check methods
    - Improve error handling and logging
    - Maintain backward compatibility
  • Updated processor service (processor.py) to utilize the new configuration system
  • Added requirements for python-dotenv
  • Created .env.example template for environment configuration
  • These changes enable easy configuration for different environments (local, Docker, production) while maintaining existing functionality
- 2026-05-11 (AG Session 1): Code review, bug fixes, and improvements to make the project runnable locally:
  • Created missing `__init__.py` files in all 5 package directories (backend/, routers/, services/, db/, models/) — without these, Python could not resolve any imports
  • Fixed `backend/main.py`: changed absolute imports to relative imports
  • Fixed `backend/routers/upload.py`: changed absolute import to relative import
  • Fixed `backend/services/chunker.py`: updated import from deprecated `langchain.text_splitter` to `langchain_text_splitters`
  • Fixed `requirements.txt`: added missing dependencies — `pdf2image`, `Pillow`, `numpy`
  • Fixed `Dockerfile`: corrected CMD from `main:app` to `backend.main:app`
  • Fixed `backend/db/elastic_client.py`: replaced deprecated `body=` parameter with keyword arguments for Elasticsearch 8.x compatibility
  • Added CORS middleware to `backend/main.py` so the frontend can communicate with the backend API
  • Added static file serving in `backend/main.py` to serve the frontend from `/frontend/`
  • Created `frontend/index.html` — a single-page dark-theme UI with document upload, query interface, and results display
  • Created `.env` file from `.env.example` for local development (localhost defaults)
  • Installed all missing pip packages into the venv
  • Verified: app starts with `uvicorn backend.main:app`, health check responds, frontend loads and connects to backend
- 2026-05-11 (AG Session 2): Comprehensive code improvements and documentation update:
  • Fixed `requirements.txt`: added missing `langchain-text-splitters` package (separate from `langchain` in v0.2+, required by chunker.py)
  • Fixed `backend/models/schemas.py`: updated `mode` field description to include 'liberal' option (was missing despite being implemented)
  • Fixed `backend/routers/query.py`: replaced all `print()` calls with proper `logger.error()` using Python's logging framework
  • Fixed `backend/db/elastic_client.py`: simplified confusing no-op expression in `create_index` mappings logic
  • Enhanced `backend/main.py`:
    - Root path (`/`) now redirects to frontend UI instead of returning JSON
    - Health check (`/health`) now reports individual service statuses (Elasticsearch, MongoDB, Qdrant) with overall degraded/healthy status
  • Updated `frontend/index.html`:
    - Added 🎓 Liberal mode button to the mode selector
    - Added liberal mode response rendering with two-section layout (Document-Based Answer + Additional Explanation)
    - Added citation display with document name, page, and chunk text preview
    - Added CSS styles for liberal mode sections, tags, and citation items
  • Updated `docker-compose.yml`:
    - Added Ollama LLM Runtime service (ollama/ollama:latest) on port 11434
    - Added OLLAMA_HOST env var to backend service
    - Added ollama_data volume for model persistence
    - Backend now depends_on ollama
  • Rewrote `flow.md` with complete documentation including:
    - Phase 3B (Liberal Mode) data flow
    - Updated file roles and responsibilities
    - Updated "How to Run Locally" with Ollama instructions
    - Updated summary table with Liberal Mode layer
  • Updated `memory.md` with this session's changes
  • Updated `planning/PROGRESS.md` to mark Phase 3B as complete