# Project Flow & Directory Structure (Current Implementation)

This document provides an overview of the repository layout **as of the work completed so far** (Phase 1 – Document Ingestion Pipeline). It explains the purpose of each existing directory and file, and will be updated as new features are added.

---

## Root Directory

| File / Folder | Purpose |
|---------------|---------|
| **PROJECT_PLAN.md** | Master plan covering all phases, architecture, tech stack, and checklists for the full RAG platform. |
| **PHASE1_SPEC.md** | Detailed specification for Phase 1 (Document Ingestion Pipeline). |
| **flow.md** | This file – a map of the current project directory structure and the role of each file/folder. |
| **memory.md** | Lightweight log of what has been implemented in each session (used to track progress). |
| **requirements.txt** | Python package dependencies for the backend (FastAPI, PyMuPDF, sentence‑transformers, Qdrant client, etc.). |
| **demo.py** | Simple script used for quick testing or demonstrations. |
| **uploads/** | Directory where uploaded documents are stored temporarily before processing (created at runtime). |
| **venv/** | Python virtual environment (not committed to the repo). |

> **Note:** Files such as `docker-compose.yml`, `.env`, and frontend-related items are planned for later phases and are not present yet.

---

## Backend (`backend/`)

Contains all server‑side code written in Python with FastAPI. Only the ingestion pipeline (Phase 1) has been implemented.

```
backend/
├── main.py                 # FastAPI application entry point; includes routers and health check.
├── routers/
│   ├── upload.py           # Handles file upload endpoints and triggers the ingestion pipeline.
│   └── query.py            # Placeholder for query endpoints (to be built in Phase 2).
├── services/
│   ├── extractor.py        # Text extraction logic (PyMuPDF, pdfplumber, Tesseract OCR, python-docx, plain TXT).
│   ├── chunker.py          # Semantic chunking using LangChain's RecursiveCharacterTextSplitter (with overlap).
│   ├── embedder.py         # Embedding generation via sentence‑transformers (BAAI/bge-large-en-v1.5).
│   └── processor.py        # Orchestrates the full pipeline: extract → chunk → embed → store in Qdrant, MongoDB, Elasticsearch.
├── db/
│   ├── qdrant_client.py    # Wrapper around Qdrant vector DB (collection management, upsert, search).
│   ├── mongo_client.py     # Wrapper around MongoDB for metadata and raw chunk storage.
│   └── elastic_client.py   # Wrapper around Elasticsearch for BM25 keyword search.
├── models/
│   └── # (empty) – Pydantic models for request/response validation will be added in later phases.
└── # Dockerfile not yet created (planned for Phase 5).
```

### Backend Data Flow (Phase 1 – Ingestion)

1. **`routers/upload.py`** receives a file via `POST /api/upload`.  
2. It saves the file to `uploads/` and calls **`services/processor.process_uploaded_file`**.  
3. **`processor.py`** coordinates:
   - **`services.extractor.extract_text`** → raw text.
   - **`services.chunker.chunk_text_with_metadata`** → list of chunk dicts (text + base metadata).  
   - **`services.embedder.embed_texts`** → NumPy array of vectors (1024‑dim).  
   - Stores vectors in **Qdrant** (`db/qdrant_client.py`).  
   - Stores chunk text + metadata in **MongoDB** (`db/mongo_client.py`).  
   - Indexes chunk text for BM25 in **Elasticsearch** (`db/elastic_client.py`).  
4. The router returns a JSON response with `document_id`, `filename`, processing status, and number of chunks.

---

## Frontend (`frontend/`)

> **Not yet implemented.**  
> The frontend will be a React application built with Tailwind CSS (planned for Phase 4). When created, it will include components for upload, mode selection, query input, answer viewing, and document management.

---

## Summary of Responsibilities by Layer (Implemented)

| Layer | Responsibility | Key Files |
|-------|----------------|-----------|
| **API Layer** | HTTP routing, request validation, orchestration calls | `backend/main.py`, `backend/routers/upload.py`, `backend/routers/query.py` (placeholder) |
| **Extraction** | Convert uploaded files (PDF, DOCX, TXT) to raw text | `backend/services/extractor.py` |
| **Chunking** | Split text into overlapping pieces and attach metadata | `backend/services/chunker.py` |
| **Embedding** | Transform chunk text into dense vectors | `backend/services/embedder.py` |
| **Storage** | Persist vectors, metadata, and keyword indexes | `backend/db/qdrant_client.py`, `backend/db/mongo_client.py`, `backend/db/elastic_client.py` |
| **Processing Pipeline** | Glue the above steps together; called from upload router | `backend/services/processor.py` |
| **Frontend UI** | *(Not yet implemented)* | — |
| **DevOps / Deploy** | *(Not yet implemented)* | — |
| **Documentation & Tracking** | Project plan, phase specs, implementation log, flow overview | `PROJECT_PLAN.md`, `PHASE1_SPEC.md`, `memory.md`, `flow.md` |

---

## How to Walk Through a Request (Ingestion)

1. **User** → POST `/api/upload` (handled by `upload.py`).  
2. **`upload.py`** saves the file and invokes `processor.process_uploaded_file`.  
3. **`processor.py`** calls:  
   - `extractor.extract_text`  
   - `chunker.chunk_text_with_metadata`  
   - `embedder.embed_texts`  
   - Stores results via the three DB clients.  
4. **Response** includes `document_id` and chunk count, confirming successful storage.

*When query functionality (Phase 2+) is added, the flow will involve retrieving from Elasticsearch (BM25) and Qdrant (vector), merging & deduplicating, reranking, and passing top chunks to the appropriate mode pipeline.*

---

*This document is a living artifact; update it as the project evolves or as new folders/files are added.*  