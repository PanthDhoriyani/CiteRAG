# CiteRAG — Project Progress Tracker

> **Last Updated:** 2026-05-11  
> **Overall Progress:** Phase 1, 2, & 3B complete. Phase 3A is next.

---

## Progress Overview

```
Phase 1: Document Ingestion Pipeline    ██████████ 100% ✅
Phase 2: Hybrid Retrieval & Reranking   ██████████ 100% ✅
Phase 3B: Liberal Analysis Mode         ██████████ 100% ✅
Phase 3A: Strict Analysis Mode          ░░░░░░░░░░   0% ← NEXT
Phase 4: Full Frontend UI               ███░░░░░░░  30% (basic UI with liberal mode exists)
Phase 5: Docker Deployment              ████░░░░░░  40% (Dockerfile + compose + Ollama exist)
```

---

## ✅ Phase 1 — Document Ingestion Pipeline (COMPLETE)

Everything needed to upload, extract, chunk, embed, and store documents.

| # | Task | Status | Key Files |
|---|------|--------|-----------| 
| 1.1 | File Upload Endpoint (`POST /api/upload`) | ✅ Done | `backend/routers/upload.py` |
| 1.2 | Text Extraction (PyMuPDF → pdfplumber → Tesseract OCR → DOCX → TXT) | ✅ Done | `backend/services/extractor.py` |
| 1.3 | Metadata Extraction (document_id, chunk_index, domain, timestamps) | ✅ Done | Embedded in `processor.py` & `chunker.py` |
| 1.4 | Semantic Chunking (512 tokens, 128 overlap, RecursiveCharacterTextSplitter) | ✅ Done | `backend/services/chunker.py` |
| 1.5 | Embedding Generation (BAAI/bge-large-en-v1.5, 1024-dim vectors) | ✅ Done | `backend/services/embedder.py` |
| 1.6 | Storage — Qdrant (vectors) + MongoDB (metadata) + Elasticsearch (BM25) | ✅ Done | `backend/db/qdrant_client.py`, `mongo_client.py`, `elastic_client.py` |

---

## ✅ Phase 2 — Hybrid Retrieval & Reranking (COMPLETE)

Everything needed to query documents with keyword, semantic, or hybrid search + reranking.

| # | Task | Status | Key Files |
|---|------|--------|-----------| 
| 2.1 | Query Input Endpoint (`POST /api/query`) | ✅ Done | `backend/routers/query.py` |
| 2.2 | BM25 Keyword Retrieval (Elasticsearch) | ✅ Done | `backend/services/retriever.py` |
| 2.3 | Vector Semantic Retrieval (Qdrant + BGE embeddings) | ✅ Done | `backend/services/retriever.py` |
| 2.4 | Merge & Deduplicate Results (union of BM25 + vector, weighted scoring) | ✅ Done | `backend/services/retriever.py` |
| 2.5 | Cross-Encoder Reranking (BAAI/bge-reranker-large) | ✅ Done | `backend/services/reranker.py` |
| 2.6 | Pydantic Request/Response Models (QueryRequest, QueryResponse, SearchResult) | ✅ Done | `backend/models/schemas.py` |

---

## ✅ Phase 3B — Liberal Analysis Mode (COMPLETE)

Educational, explanation-friendly answers that combine document evidence with AI reasoning.

| # | Task | Status | Key Files |
|---|------|--------|-----------| 
| 3B.1 | Document-Based Answer Generation | ✅ Done | `backend/services/liberal_mode.py` |
| 3B.2 | LLM Knowledge Expansion | ✅ Done | `backend/services/liberal_mode.py` |
| 3B.3 | Source Transparency | ✅ Done | Response separates document-based vs AI-added content |
| 3B.4 | Liberal Mode Output Structure | ✅ Done | Two sections: "Document-Based Answer" + "Additional Explanation" |
| 3B.5 | Liberal Mode System Prompt | ✅ Done | Educational assistant prompt in `liberal_mode.py` |
| 3B.6 | Pydantic Models for Liberal Response | ✅ Done | `LiberalAnswer`, `LiberalQueryResponse` in `schemas.py` |
| 3B.7 | Frontend Liberal Mode UI | ✅ Done | Mode button + two-section response display + citations |
| 3B.8 | Ollama Integration | ✅ Done | HTTP client in `liberal_mode.py`, Ollama in `docker-compose.yml` |

### How Liberal Mode Works
1. User submits query with `mode="liberal"` → `query.py`
2. Hybrid search retrieves relevant chunks → `retriever.py`
3. Cross-encoder reranks results → `reranker.py`
4. Top chunks sent as context to Ollama LLM → `liberal_mode.py`
5. LLM response parsed into document-based + additional explanation sections
6. Structured response returned with citations and metadata

### Prerequisites for Liberal Mode
- **Ollama** installed and running (`ollama serve` or via Docker)
- **LLM model** pulled (e.g., `ollama pull llama3:8b`)

---

## ✅ Bug Fixes & Infra Improvements (COMPLETE)

Code review and fixes to make the project actually runnable locally.

| # | Task | Status | Details |
|---|------|--------|---------|
| AG-1 | Created 5 missing `__init__.py` files | ✅ Fixed | backend/, routers/, services/, db/, models/ |
| AG-2 | Fixed broken imports (absolute → relative) | ✅ Fixed | `main.py`, `upload.py` |
| AG-3 | Fixed deprecated `langchain.text_splitter` import | ✅ Fixed | `chunker.py` → `langchain_text_splitters` |
| AG-4 | Added missing pip dependencies | ✅ Fixed | `pdf2image`, `Pillow`, `numpy`, `langchain-text-splitters` in `requirements.txt` |
| AG-5 | Fixed Dockerfile CMD path | ✅ Fixed | `main:app` → `backend.main:app` |
| AG-6 | Fixed Elasticsearch deprecated `body=` param | ✅ Fixed | `elastic_client.py` — uses keyword args for ES 8.x |
| AG-7 | Added CORS middleware | ✅ Done | `main.py` — allows frontend to call API |
| AG-8 | Added static file serving | ✅ Done | `main.py` — serves `/frontend/` directory |
| AG-9 | Created basic frontend UI | ✅ Done | `frontend/index.html` — upload, query, results |
| AG-10 | Created `.env` for local dev | ✅ Done | Localhost defaults from `.env.example` |
| AG-11 | Installed all packages in venv | ✅ Done | All imports verified working |
| AG-12 | Fixed `query.py` logging | ✅ Fixed | Replaced `print()` with proper `logger.error()` |
| AG-13 | Fixed `elastic_client.py` mappings logic | ✅ Fixed | Removed confusing no-op expression |
| AG-14 | Enhanced health check endpoint | ✅ Done | Reports individual DB connection statuses |
| AG-15 | Root path redirects to frontend | ✅ Done | `GET /` → `302 /frontend/index.html` |
| AG-16 | Added Liberal mode to frontend | ✅ Done | Mode button + response renderer + citations |
| AG-17 | Added Ollama to docker-compose | ✅ Done | `ollama/ollama:latest` on port 11434 |
| AG-18 | Updated `mode` field in schema | ✅ Fixed | Description now includes 'liberal' option |

---

## 🔲 Phase 3A — Strict Analysis Mode (NOT STARTED — DO THIS NEXT)

Enterprise-grade, hallucination-free, citation-mandatory, publicly verified answers.

| # | Task | Status | What to Build |
|---|------|--------|---------------|
| 3A.1 | Citation Grounding Validation | 🔲 TODO | Check if retrieved chunks contain enough evidence; reject if insufficient (reranker score < 0.65) |
| 3A.2 | Trusted Public Source Verification | 🔲 TODO | Query PubMed, arXiv, IEEE, gov portals based on document domain |
| 3A.3 | Consistency Check | 🔲 TODO | Compare document claims vs public source evidence (Verified / Contradiction / Insufficient) |
| 3A.4 | Confidence Scoring | 🔲 TODO | Calculate 0.0–1.0 score based on reranker score, supporting chunks, verification result |
| 3A.5 | Grounded LLM Generation | 🔲 TODO | Strict system prompt — answer ONLY from evidence, no speculation |
| 3A.6 | Strict Mode Output Structure | 🔲 TODO | Answer + Citation + Public Source + Consistency Status + Confidence Score |

### Prerequisites for Phase 3A
- Phase 3B must be working first (validates the LLM integration) ✅
- API keys or access to PubMed, arXiv, IEEE Xplore, Semantic Scholar
- New files to create: `backend/services/strict_mode.py`, `backend/services/verifier.py`

---

## 🔲 Phase 4 — Full Frontend UI (NOT STARTED — basic UI exists)

| # | Task | Status | What to Build |
|---|------|--------|---------------|
| 4.1 | Upload Zone Component | ✅ Basic done | Full React component with progress bar, domain tagging |
| 4.2 | Mode Toggle (Strict / Liberal) | ✅ Basic done | Prominent toggle with mode descriptions |
| 4.3 | Query Input with Filters | ✅ Basic done | Add domain filter, document filter dropdowns |
| 4.4 | Strict Mode Answer Viewer | 🔲 TODO | Citation cards, public source links, consistency badges, confidence bar |
| 4.5 | Liberal Mode Answer Viewer | ✅ Done | Two-section layout: "From your document" + "Additional context" |
| 4.6 | Document Manager | 🔲 TODO | List uploaded docs, delete, re-index |
| 4.7 | API Integration | ✅ Basic done | Connect all new endpoints |

### Note
> The current `frontend/index.html` is a functional UI with support for all 4 query modes (Hybrid, Vector, BM25, Liberal). Phase 4 in the plan calls for a full **React + Tailwind CSS** application. This can be done after 3A is working.

---

## 🔲 Phase 5 — Docker Deployment (PARTIALLY DONE)

| # | Task | Status | What to Build |
|---|------|--------|---------------|
| 5.1 | Dockerfile for FastAPI backend | ✅ Done | `Dockerfile` |
| 5.2 | Dockerfile for React frontend | 🔲 TODO | Depends on Phase 4 |
| 5.3 | docker-compose.yml with all services | ✅ Done | Has backend + Qdrant + MongoDB + ES + Ollama |
| 5.4 | .env file configured | ✅ Done | `.env` |
| 5.5 | Volume mounts for data persistence | ✅ Done | Qdrant, MongoDB, ES, Ollama volumes defined |
| 5.6 | Ollama model pre-pull on startup | 🔲 TODO | Auto-pull script or init container |
| 5.7 | Health checks for all services | ⬜ Partial | API health check done, Docker health check commands TODO |

---

## Recommended Next Steps (In Order)

```
1. ✅ Install Ollama locally → ollama pull llama3:8b
2. ✅ Build Phase 3B (Liberal Mode) → services/liberal_mode.py
3. Test: upload a doc → query with liberal mode → get LLM-generated answer
4. Build Phase 3A (Strict Mode) → services/strict_mode.py, services/verifier.py
5. Build Phase 4 (Full React Frontend)
6. Finalize Phase 5 (Docker everything)
7. Testing & Tuning (chunk size, reranker threshold, confidence cutoff)
```

---

*This document is a living tracker. Update it as each task is completed.*
