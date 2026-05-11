# Project Flow & Directory Structure (Current Implementation)

 This project is a Citation-Aware Multi-Source RAG (Retrieval-Augmented 
  Generation) Platform. It is designed to ingest documents, index them across
  multiple database types for high-performance retrieval, and allow users to
  query that data with a hybrid search approach. It also supports a Liberal
  Analysis Mode that generates educational answers combining document evidence
  with AI-generated explanations via a local LLM (Ollama).

  📁 Project Structure & File Roles

  1. backend/ (The Core Engine)

  - main.py: The entry point. It initializes the FastAPI application,
  configures CORS, and mounts the routers and frontend static files.
  Root path (`/`) redirects to the frontend UI. Health check (`/health`)
  reports individual service statuses for Elasticsearch, MongoDB, and Qdrant.
  - routers/: Defines the API endpoints.
    - upload.py: Handles file uploads (PDF, DOCX, TXT), saves them to the
  uploads/ folder, and triggers the ingestion pipeline.
    - query.py: Handles user questions. It orchestrates retrieval (BM25,
  Vector, Hybrid, or Liberal) and re-ranking of results. For liberal mode,
  it additionally generates an LLM answer via Ollama.
  - services/: Contains the business logic for the RAG pipeline.
    - processor.py: The orchestrator that connects extraction → chunking →
  embedding → storage.
    - extractor.py: Extracts raw text from various file formats.
    - chunker.py: Splits long text into smaller, manageable chunks with
  overlapping windows to preserve context.
    - embedder.py: Converts text chunks into numerical vectors (embeddings)
  using a machine learning model.
    - retriever.py: Logic to fetch relevant chunks from Elasticsearch (keyword)
   and Qdrant (vector).
    - reranker.py: Refines the initial results to ensure the most relevant
  chunks are at the top.
    - liberal_mode.py: Generates educational answers by combining document
  evidence with AI-generated explanations via Ollama LLM. Parses responses
  into "Document-Based Answer" and "Additional Explanation" sections.
  - db/: Database clients.
    - qdrant_client.py: Interfaces with Qdrant (Vector Database) for semantic
  search.
    - mongo_client.py: Interfaces with MongoDB (Document Store) for storing
  metadata and raw chunks.
    - elastic_client.py: Interfaces with Elasticsearch for BM25 (keyword-based)
   search.
  - models/: Defines the data structures (schemas) for API requests and
  responses using Pydantic.
  - config.py: Centralized configuration settings.

  2. frontend/

  - Contains the user interface (index.html) used to upload documents and ask
  questions. Supports four query modes: Hybrid, Vector, BM25, and Liberal.

  3. Other Root Files

  - uploads/: Temporary storage for uploaded files.
  - docker-compose.yml & Dockerfile: For containerizing the application and its
   dependencies (DBs + Ollama).
  - requirements.txt: Python dependencies.
  - planning/: Design documents and progress tracking.

  ---
  ⚙️  System Flow (How it works)

  Flow A: Document Ingestion (When a user uploads a file)

  1. User Action: Uploads a file via the Frontend.
  2. Route: POST /api/upload → upload.py.
  3. Storage: The file is saved to the /uploads folder with a unique
  document_id.
  4. Processing: processor.py takes over:
    - Extraction: extractor.py reads the file and converts it to plain text.
    - Chunking: chunker.py splits the text into small chunks (e.g., 512
  tokens).
    - Embedding: embedder.py turns these text chunks into vectors.
  5. Multi-DB Indexing: The system stores the data in three places
  simultaneously:
    - Qdrant: Stores the vectors for "meaning-based" search.
    - Elasticsearch: Indexes the text for "keyword-based" search.
    - MongoDB: Stores the full text and metadata for final retrieval.
  6. Response: User receives a confirmation that the document was processed.

  Flow B: Querying — Standard Modes (BM25 / Vector / Hybrid)

  1. User Action: Types a question in the Frontend.
  2. Route: POST /api/query → query.py.
  3. Retrieval: Depending on the mode selected (BM25, Vector, or Hybrid):
    - Vector Search: Asks Qdrant for chunks that are semantically similar to
  the question.
    - BM25 Search: Asks Elasticsearch for chunks that contain the exact words
  of the question.
    - Hybrid: Combines both results.
  4. Re-ranking: reranker.py takes the top results and uses a more powerful
  model to re-score them, ensuring the most accurate answer is first.
  5. Result: The system returns the top-ranked chunks (and their
  metadata/citations) back to the user.

  Flow C: Querying — Liberal Mode (Document + AI Answer)

  1. User Action: Types a question in the Frontend with "Liberal" mode selected.
  2. Route: POST /api/query (mode="liberal") → query.py.
  3. Retrieval: Hybrid search is used to get initial results.
  4. Re-ranking: reranker.py refines the results.
  5. LLM Generation: liberal_mode.py sends the top chunks as context to Ollama:
    - Creates a structured prompt instructing the LLM to separate document-based
      answers from AI-added explanations.
    - Calls Ollama API (e.g., llama3:8b model).
    - Parses the response into two sections.
  6. Result: Returns a structured response with:
    - "Document-Based Answer" (from uploaded document only)
    - "Additional Explanation" (AI-generated broader context)
    - Citations (document name, page, chunk text)
    - Metadata (model used, processing time)



---

## Root Directory

| File / Folder | Purpose |
|---------------|---------|
| **planning/PROJECT_PLAN.md** | Master plan covering all phases, architecture, tech stack, and checklists for the full RAG platform. |
| **planning/PROGRESS.md** | Detailed progress tracker for all phases and tasks. |
| **planning/PHASE1_SPEC.md** | Detailed specification for Phase 1 (Document Ingestion Pipeline). |
| **planning/PHASE3B_SPEC.md** | Detailed specification for Phase 3B (Liberal Analysis Mode). |
| **flow.md** | This file – a map of the current project directory structure and the role of each file/folder. |
| **memory.md** | Lightweight log of what has been implemented in each session (used to track progress). |
| **requirements.txt** | Python package dependencies. |
| **.env.example** | Example environment variable configuration file (copy to .env and customize). |
| **.env** | Local development environment variables (created from .env.example with localhost defaults). |
| **Dockerfile** | Docker image definition for the backend. |
| **docker-compose.yml** | Docker Compose setup for backend + Qdrant + MongoDB + Elasticsearch + Ollama. |
| **uploads/** | Directory where uploaded documents are stored temporarily before processing (created at runtime). |
| **venv/** | Python virtual environment (not committed to the repo). |
| **test_*.py** | Test files for integration, liberal mode, and query router testing. |

---

## Backend (`backend/`)

Contains all server‑side code written in Python with FastAPI. Phase 1 (ingestion), Phase 2 (retrieval & reranking), and Phase 3B (liberal analysis mode) have been implemented.

```
backend/
├── __init__.py             # Package init file — required for relative imports to work.
├── main.py                 # FastAPI entry point; includes routers, CORS, static file serving, health check with DB statuses.
├── config.py               # Centralized configuration management using environment variables.
├── routers/
│   ├── __init__.py         # Package init file.
│   ├── upload.py           # File upload endpoint — validates type, saves file, triggers processing.
│   └── query.py            # Query endpoint for hybrid retrieval with re-ranking + liberal mode support.
├── services/
│   ├── __init__.py         # Package init file with exports.
│   ├── extractor.py        # Text extraction logic (PyMuPDF, pdfplumber, Tesseract OCR, python-docx, plain TXT).
│   ├── chunker.py          # Smart chunking using LangChain's RecursiveCharacterTextSplitter.
│   ├── embedder.py         # Embedding generation via sentence‑transformers (BAAI/bge-large-en-v1.5).
│   ├── processor.py        # Orchestrates ingestion pipeline: extract → chunk → embed → store.
│   ├── retriever.py        # Hybrid retrieval combining BM25 (Elasticsearch) and vector (Qdrant) search.
│   ├── reranker.py         # Cross-encoder re-ranking using BAAI/bge-reranker-large.
│   └── liberal_mode.py     # Liberal Analysis Mode — LLM answer generation via Ollama with document grounding.
├── db/
│   ├── __init__.py         # Package init file.
│   ├── qdrant_client.py    # Wrapper around Qdrant vector DB (collection management, upsert, search).
│   ├── mongo_client.py     # Wrapper around MongoDB for metadata and raw chunk storage.
│   └── elastic_client.py   # Elasticsearch wrapper — uses keyword args for ES 8.x compatibility.
├── models/
│   ├── __init__.py         # Package init file with exports.
│   └── schemas.py          # Pydantic models: QueryRequest, QueryResponse, SearchResult, LiberalAnswer, LiberalQueryResponse.
```

### Backend Data Flow (Phase 1 – Ingestion)

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

### Backend Data Flow (Phase 2 – Query & Retrieval)

1. **`routers/query.py`** receives a question via `POST /api/query`.
2. **`services/retriever.py`** performs search based on selected mode:
   - **BM25 mode**: searches Elasticsearch for keyword matches.
   - **Vector mode**: embeds the query and searches Qdrant for semantic similarity.
   - **Hybrid mode**: combines both BM25 and vector scores with configurable weights.
3. **`services/reranker.py`** re-ranks the results using a cross-encoder model.
4. The router returns ranked results with scores, text, and metadata.

### Backend Data Flow (Phase 3B – Liberal Analysis Mode)

1. **`routers/query.py`** receives a question with `mode="liberal"`.
2. Hybrid search + re-ranking is performed (same as above).
3. **`services/liberal_mode.py`** takes the top reranked chunks and:
   - Formats them into a context block with source citations.
   - Creates a structured prompt that instructs the LLM to separate document-based from AI-added content.
   - Calls the **Ollama API** (`http://localhost:11434/api/generate`).
   - Parses the LLM response into `document_based` and `additional_explanation` sections.
4. Returns a `LiberalQueryResponse` with the structured answer, citations, and metadata.

### Configuration System

The application uses a centralized configuration system:
- **`config.py`**: Loads configuration from environment variables with `.env` file support
- **Database clients**: Accept optional connection parameters, falling back to configuration values
- **Environment variables**: Control all connection settings (hosts, ports, database names, etc.)
- **Example configuration**: See `.env.example` for all available options

---

## Frontend (`frontend/`)

> Single-page HTML/CSS/JS frontend served by FastAPI's static file serving.

```
frontend/
└── index.html              # Dark-theme glassmorphism UI with upload, query, and results display.
```

### Frontend Features
- **Document Upload Zone**: Drag-and-drop or click-to-browse file upload (PDF, DOCX, TXT)
- **Mode Selector**: Toggle between Hybrid, Vector, BM25, and Liberal search modes
- **Query Input**: Text input with search button
- **Results Display**: 
  - Standard modes: Ranked results with scores, text preview, and metadata
  - Liberal mode: Two-section layout with "Document-Based Answer" + "Additional Explanation" + citations
- **Backend Health Indicator**: Real-time connection status (green/red dot)
- **Toast Notifications**: Success/error feedback for uploads and queries
- **Access**: `http://localhost:8000/frontend/index.html` (or just `http://localhost:8000/` which redirects)

---

## Summary of Responsibilities by Layer (Implemented)

| Layer | Responsibility | Key Files |
|-------|----------------|-----------|
| **API Layer** | HTTP routing, request validation, orchestration calls | `backend/main.py`, `backend/routers/upload.py`, `backend/routers/query.py` |
| **Configuration** | Centralized configuration management | `backend/config.py`, `.env.example`, `.env` |
| **Extraction** | Convert uploaded files (PDF, DOCX, TXT) to raw text | `backend/services/extractor.py` |
| **Chunking** | Split text into overlapping pieces and attach metadata | `backend/services/chunker.py` |
| **Embedding** | Transform chunk text into dense vectors | `backend/services/embedder.py` |
| **Retrieval** | Hybrid search combining BM25 + vector search | `backend/services/retriever.py` |
| **Re-ranking** | Cross-encoder re-ranking for precision | `backend/services/reranker.py` |
| **Liberal Mode** | LLM-based answer generation with document grounding | `backend/services/liberal_mode.py` |
| **Storage** | Persist vectors, metadata, and keyword indexes | `backend/db/qdrant_client.py`, `backend/db/mongo_client.py`, `backend/db/elastic_client.py` |
| **Processing Pipeline** | Glue the above steps together; called from upload router | `backend/services/processor.py` |
| **Frontend UI** | Document upload, query, results display (4 modes) | `frontend/index.html` |
| **DevOps / Deploy** | Dockerfile, docker-compose with all services | `Dockerfile`, `docker-compose.yml` |
| **Documentation & Tracking** | Project plan, phase specs, implementation log, flow overview | `planning/PROJECT_PLAN.md`, `planning/PROGRESS.md`, `memory.md`, `flow.md` |

---

## How to Run Locally

```bash
# 1. Activate virtual environment
.\venv\Scripts\activate

# 2. Start infrastructure services (Qdrant, MongoDB, Elasticsearch)
docker-compose up -d qdrant mongo elasticsearch

# 3. (Optional) Start Ollama for Liberal mode
#    Option A: Via Docker
docker-compose up -d ollama
#    Option B: Locally installed Ollama
ollama serve
#    Then pull a model:
ollama pull llama3:8b

# 4. Start the backend (from project root)
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# 5. Open in browser
#    Frontend UI:  http://127.0.0.1:8000/frontend/index.html
#    Swagger Docs: http://127.0.0.1:8000/docs
#    Health Check: http://127.0.0.1:8000/health
```

---

## How to Walk Through a Request (Ingestion)

1. **User** → POST `/api/upload` (handled by `upload.py`).  
2. **`upload.py`** saves the file and invokes `processor.process_uploaded_file`.  
3. **`processor.py`** coordinates:  
   - `extractor.extract_text`  
   - `chunker.chunk_text_with_metadata`  
   - `embedder.embed_texts`  
   - Stores results via the three DB clients (using configuration values)  
4. **Response** includes `document_id`, `filename`, processing status, and number of chunks.

## How to Walk Through a Request (Query — Standard)

1. **User** → POST `/api/query` (handled by `query.py`).
2. **`query.py`** initializes retriever and reranker (lazy loading).
3. **`retriever.py`** performs BM25, vector, or hybrid search depending on mode.
4. **`reranker.py`** re-ranks results using cross-encoder scores.
5. **Response** includes ranked results with scores, text, metadata, and processing time.

## How to Walk Through a Request (Query — Liberal Mode)

1. **User** → POST `/api/query` with `mode="liberal"` (handled by `query.py`).
2. **`query.py`** initializes retriever, reranker, and liberal mode service (lazy loading).
3. **`retriever.py`** performs hybrid search.
4. **`reranker.py`** re-ranks the results.
5. **`liberal_mode.py`** generates an answer via Ollama LLM:
   - Formats context from top chunks
   - Creates educational prompt
   - Calls Ollama API
   - Parses response into document-based + additional explanation sections
6. **Response** includes structured answer, citations, LLM model info, and processing time.

---

*This document is a living artifact; update it as the project evolves or as new folders/files are added.*