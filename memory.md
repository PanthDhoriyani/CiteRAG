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
- 2026-05-09: Created flow.md (root) explaining the project directory structure, file purposes, and data flow for backend (Phase 1 only). Updated to reflect only implemented files/folders.
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
- 2026-05-11 (AG): Code review, bug fixes, and improvements to make the project runnable locally:
  • (AG) Created missing `__init__.py` files in all 5 package directories (backend/, routers/, services/, db/, models/) — without these, Python could not resolve any imports
  • (AG) Fixed `backend/main.py`: changed absolute imports (`from routers import ...`) to relative imports (`from .routers import ...`)
  • (AG) Fixed `backend/routers/upload.py`: changed absolute import (`from services.processor`) to relative import (`from ..services.processor`)
  • (AG) Fixed `backend/services/chunker.py`: updated import from deprecated `langchain.text_splitter` to `langchain_text_splitters`
  • (AG) Fixed `requirements.txt`: added missing dependencies — `pdf2image`, `Pillow`, `numpy` (were imported in code but not listed)
  • (AG) Fixed `Dockerfile`: corrected CMD from `main:app` to `backend.main:app` (main.py is inside the backend package)
  • (AG) Fixed `backend/db/elastic_client.py`: replaced deprecated `body=` parameter with keyword arguments (`document=`, `query=`, `size=`, `mappings=`) for Elasticsearch 8.x compatibility
  • (AG) Added CORS middleware to `backend/main.py` so the frontend can communicate with the backend API
  • (AG) Added static file serving in `backend/main.py` to serve the frontend from `/frontend/`
  • (AG) Created `frontend/index.html` — a single-page dark-theme UI with document upload (drag-and-drop), query interface with mode selector (Hybrid/Vector/BM25), results display, and backend health indicator
  • (AG) Created `.env` file from `.env.example` for local development (localhost defaults)
  • (AG) Installed all missing pip packages into the venv
  • (AG) Verified: app starts with `uvicorn backend.main:app`, health check responds, frontend loads and connects to backend