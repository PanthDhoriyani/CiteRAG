# CiteRAG — Project Progress Tracker

> **Last Updated:** 2026-05-11  
> **Overall Progress:** Phase 1 & 2 complete, Phase 3B is next.

---

## Progress Overview

```
Phase 1: Document Ingestion Pipeline    ██████████ 100% ✅
Phase 2: Hybrid Retrieval & Reranking   ██████████ 100% ✅
Phase 3B: Liberal Analysis Mode         ░░░░░░░░░░   0% ← NEXT
Phase 3A: Strict Analysis Mode          ░░░░░░░░░░   0%
Phase 4: Full Frontend UI               ██░░░░░░░░  20% (basic UI exists)
Phase 5: Docker Deployment              ██░░░░░░░░  20% (Dockerfile + compose exist)
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

## ✅ Bug Fixes & Infra Improvements (COMPLETE — by AG)

Code review and fixes to make the project actually runnable locally.

| # | Task | Status | Details |
|---|------|--------|---------|
| AG-1 | Created 5 missing `__init__.py` files | ✅ Fixed | backend/, routers/, services/, db/, models/ |
| AG-2 | Fixed broken imports (absolute → relative) | ✅ Fixed | `main.py`, `upload.py` |
| AG-3 | Fixed deprecated `langchain.text_splitter` import | ✅ Fixed | `chunker.py` → `langchain_text_splitters` |
| AG-4 | Added missing pip dependencies | ✅ Fixed | `pdf2image`, `Pillow`, `numpy` in `requirements.txt` |
| AG-5 | Fixed Dockerfile CMD path | ✅ Fixed | `main:app` → `backend.main:app` |
| AG-6 | Fixed Elasticsearch deprecated `body=` param | ✅ Fixed | `elastic_client.py` — uses keyword args for ES 8.x |
| AG-7 | Added CORS middleware | ✅ Done | `main.py` — allows frontend to call API |
| AG-8 | Added static file serving | ✅ Done | `main.py` — serves `/frontend/` directory |
| AG-9 | Created basic frontend UI | ✅ Done | `frontend/index.html` — upload, query, results |
| AG-10 | Created `.env` for local dev | ✅ Done | Localhost defaults from `.env.example` |
| AG-11 | Installed all packages in venv | ✅ Done | All imports verified working |

---

## 🔲 Phase 3B — Liberal Analysis Mode (NOT STARTED — DO THIS NEXT)

> **Why 3B before 3A?** Liberal mode lets you validate the full RAG loop (retrieval → LLM generation → output) without needing external API integrations. Once that works, layer on verification for Strict Mode.

| # | Task | Status | What to Build |
|---|------|--------|---------------|
| 3B.1 | Document-Based Answer Generation | 🔲 TODO | Send top reranked chunks as context to Ollama LLM, generate an answer grounded in the document |
| 3B.2 | LLM Knowledge Expansion | 🔲 TODO | Allow AI to add simplified explanations, background context, analogies beyond the document |
| 3B.3 | Source Transparency | 🔲 TODO | Clearly label what came from the document vs what is AI-added general knowledge |
| 3B.4 | Liberal Mode Output Structure | 🔲 TODO | Format response into two sections: "Document-Based Answer" + "Additional Explanation" |
| 3B.5 | Liberal Mode System Prompt | 🔲 TODO | Create the educational assistant prompt that prioritizes document content but allows broader reasoning |

### Prerequisites for Phase 3B
- **Ollama** installed and running locally (`ollama serve`)
- **LLM model** pulled (e.g., `ollama pull llama3:8b` or `ollama pull mistral`)
- New files to create: `backend/services/liberal_mode.py`, update `backend/routers/query.py`

---

## 🔲 Phase 3A — Strict Analysis Mode (NOT STARTED)

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
- Phase 3B must be working first (validates the LLM integration)
- API keys or access to PubMed, arXiv, IEEE Xplore, Semantic Scholar
- New files to create: `backend/services/strict_mode.py`, `backend/services/verifier.py`

---

## 🔲 Phase 4 — Full Frontend UI (NOT STARTED — basic UI exists)

| # | Task | Status | What to Build |
|---|------|--------|---------------|
| 4.1 | Upload Zone Component | ✅ Basic done (AG) | Full React component with progress bar, domain tagging |
| 4.2 | Mode Toggle (Strict / Liberal) | 🔲 TODO | Prominent toggle with mode descriptions |
| 4.3 | Query Input with Filters | ✅ Basic done (AG) | Add domain filter, document filter dropdowns |
| 4.4 | Strict Mode Answer Viewer | 🔲 TODO | Citation cards, public source links, consistency badges, confidence bar |
| 4.5 | Liberal Mode Answer Viewer | 🔲 TODO | Two-section layout: "From your document" + "Additional context" |
| 4.6 | Document Manager | 🔲 TODO | List uploaded docs, delete, re-index |
| 4.7 | API Integration | ✅ Basic done (AG) | Connect all new endpoints |

### Note
> The current `frontend/index.html` (created by AG) is a functional basic UI. Phase 4 in the plan calls for a full **React + Tailwind CSS** application. This can be done after 3A & 3B are working.

---

## 🔲 Phase 5 — Docker Deployment (PARTIALLY DONE)

| # | Task | Status | What to Build |
|---|------|--------|---------------|
| 5.1 | Dockerfile for FastAPI backend | ✅ Done (AG fixed) | `Dockerfile` |
| 5.2 | Dockerfile for React frontend | 🔲 TODO | Depends on Phase 4 |
| 5.3 | docker-compose.yml with all services | ⬜ Partial | Has backend + Qdrant + MongoDB + ES. Missing: frontend, Ollama |
| 5.4 | .env file configured | ✅ Done (AG) | `.env` |
| 5.5 | Volume mounts for data persistence | ✅ Done | Qdrant, MongoDB, ES volumes defined |
| 5.6 | Ollama model pre-pull on startup | 🔲 TODO | Add Ollama service to docker-compose |
| 5.7 | Health checks for all services | 🔲 TODO | Docker health check commands |

---

## Recommended Next Steps (In Order)

```
1. Install Ollama locally → ollama pull llama3:8b
2. Build Phase 3B (Liberal Mode) → services/liberal_mode.py
3. Test: upload a doc → query → get LLM-generated answer
4. Build Phase 3A (Strict Mode) → services/strict_mode.py, services/verifier.py
5. Build Phase 4 (Full React Frontend)
6. Finalize Phase 5 (Docker everything)
7. Testing & Tuning (chunk size, reranker threshold, confidence cutoff)
```

---

*This document is a living tracker. Update it as each task is completed.*
