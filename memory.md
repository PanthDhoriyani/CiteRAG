# CiteRAG — Session Memory & Change Log

> Running log of all major decisions, changes, and architectural choices made across development sessions.

---

## Session 1 — Project Foundation
**Date:** Early May 2026

### What was built
- Designed the overall RAG architecture (3-database hybrid approach)
- Set up FastAPI backend skeleton
- Implemented document ingestion pipeline:
  - Text extraction (PyMuPDF → pdfplumber → Tesseract OCR → DOCX → TXT)
  - Chunking with RecursiveCharacterTextSplitter (512 tokens, 128 overlap)
  - Embedding with BAAI/bge-large-en-v1.5 (1024-dim local model)
  - Triple storage: Qdrant + MongoDB + Elasticsearch

### Key decisions
- **Why 3 databases?** Each is specialized: Qdrant for vector similarity, ES for keyword BM25, MongoDB for metadata
- **Why 512-token chunks?** Balances context (enough meaning) vs precision (not too much noise)
- **Why BGE embeddings?** BAAI/bge-large-en-v1.5 ranks #1 on MTEB benchmark for retrieval at the time

---

## Session 2 — Hybrid Retrieval & Reranking
**Date:** Mid May 2026

### What was built
- `retriever.py` — BM25 (Elasticsearch) + Vector (Qdrant) hybrid search
- `reranker.py` — Cross-encoder reranking with BAAI/bge-reranker-large
- `POST /api/query` endpoint
- Basic frontend (`frontend/index.html`)
- Health check endpoint (`GET /health`)

### Key decisions
- **Why hybrid?** BM25 catches exact keywords (names, numbers), vector catches concepts. Hybrid misses fewer results
- **Why rerank?** First retrieval is fast but imprecise. Cross-encoder is slow but very accurate. Two-stage pipeline = speed + quality

---

## Session 3 — Stabilization & Bug Fixes
**Date:** 2026-05-11

### What was fixed
- Fixed relative import issues (package hierarchy standardization)
- Updated Elasticsearch API calls for v8 compatibility
- Installed missing dependencies
- Fixed frontend CORS and API routing issues
- Updated documentation (flow.md, memory.md, PROGRESS.md)

---

## Session 4 — Cloud Migration & LLM Integration
**Date:** 2026-05-13 (Part 1)

### What was migrated
- **MongoDB** → MongoDB Atlas (SRV connection string)
- **Elasticsearch** → Elastic Cloud (HTTPS + API key)
- **Qdrant** → Qdrant Cloud (URL + API key)

### LLM integration
- `liberal_mode.py` rewritten to support 3 providers: Ollama (local), Groq (cloud), Gemini (cloud)
- Integrated Google Gemini 2.5 Flash via `google-genai` SDK (replaced deprecated `google-generativeai`)
- Set `LLM_PROVIDER=gemini` as default in `.env`
- Resolved Gemini quota issues by switching from `gemini-2.5-pro` → `gemini-2.5-flash`

### Key decisions
- **Why Gemini Flash over Pro?** Flash is free tier, faster, and sufficient for document Q&A
- **Why cloud DBs?** Removes need for Docker, works on any machine, enables future multi-user deployment

---

## Session 5 — Document Management & 2-Mode UI
**Date:** 2026-05-13 (Part 2)

### What was built

#### Backend: Document Management API
- `GET /api/documents` — lists all unique documents via MongoDB aggregation
- `DELETE /api/documents/{id}` — deletes from MongoDB + Qdrant + Elasticsearch simultaneously
- Added `list_documents()` and `delete_document_chunks()` to `mongo_client.py`
- Added `delete_by_document_id()` to `qdrant_client.py` (FilterSelector)
- Added `delete_by_document_id()` to `elastic_client.py` (keyword + match_phrase fallback)
- New router: `backend/routers/documents.py`

#### Backend: 2-Mode Query System
- Replaced 4 modes (bm25/vector/hybrid/liberal) with clean 2-mode system
- **Strict mode** — hybrid retrieval + location metadata + Gemini search keywords
- **Liberal mode** — hybrid retrieval + Gemini 2.5 Flash full answer
- Legacy modes (bm25/vector/hybrid) still accepted by API, mapped to strict internally
- New service: `backend/services/strict_mode.py`

#### Frontend: Document Library
- Document Library panel with checkboxes per document
- Select All / None toggle
- Delete button per document with confirmation
- Filter bar showing which documents are being searched
- Passes selected `document_ids` to query payload for filtered retrieval

#### Liberal Mode Quality Improvements
- Rich Markdown prompt — Gemini now responds with headings, bold, bullets, blockquotes
- `marked.js` CDN added for client-side Markdown rendering
- Markdown CSS styles for dark theme (headings, blockquotes, code blocks, lists)

#### Meta-Query Detection
- Pattern list (`_META_PATTERNS`) detects vague questions like "explain this document"
- On detection: fetch limit × 6 chunks, reframe question as explicit overview request
- Document names always injected into LLM prompt so Gemini knows what files are loaded
- Prevents the bug: "explain this document" → generic answer about what a document is

### Key decisions
- **Why detect meta queries separately?** Vague queries return poor search results → poor LLM context. Reframing ensures Gemini gets enough content to give a real answer
- **Why marked.js instead of custom parser?** Battle-tested, handles edge cases (nested lists, code blocks), tiny bundle
- **Why delete from all 3 DBs simultaneously?** Consistency — a document must be fully deleted everywhere or it would still appear in search

---

## Configuration Reference (Current .env)

```
MONGO_URI         = mongodb+srv://...atlas.mongodb.net/...
ES_URL            = https://...elastic-cloud...
ES_API_KEY        = ...
QDRANT_URL        = https://...qdrant.io
QDRANT_API_KEY    = ...

LLM_PROVIDER      = gemini
GEMINI_API_KEY    = AIza...
GEMINI_MODEL      = gemini-2.5-flash
```

---

## Known Issues & Gotchas

| Issue | Status | Notes |
|-------|--------|-------|
| Cold start delay (2-5 min) | ⚠️ Known | BGE embedding model loads on first request. Subsequent queries are fast (~5s) |
| Image-heavy PDFs | ⚠️ Partial | Tesseract OCR covers most cases. Low-res scans may have poor extraction |
| Gemini rate limits | ✅ Handled | Flash tier has generous free quota; errors are caught and returned gracefully |
| Qdrant startup | ✅ Fixed | Cloud mode doesn't crash on startup — errors only on actual query attempts |

---

## What's Next

- **Phase 5:** React frontend (multi-tab, search history, document preview)
- **Phase 6:** Production deployment (Render/Railway backend + Vercel frontend)
- **Strict Mode Phase 2:** Page number extraction from PDF metadata, line-level citation