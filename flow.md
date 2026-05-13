# CiteRAG — System Flow & Architecture

> **Last Updated:** 2026-05-14
> Full cloud-native RAG platform with 2-mode query system, document management, and Gemini LLM integration.

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Browser)                       │
│   frontend/index.html — Single HTML file, vanilla JS + CSS      │
│                                                                  │
│  [Upload Panel]  [Document Library]  [Query Panel: 2 modes]     │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP (FastAPI REST API)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (Python FastAPI)                       │
│                                                                  │
│  POST /api/upload       → upload.py → processor.py              │
│  POST /api/query        → query.py  → retriever → reranker      │
│                                    → strict_mode / liberal_mode  │
│  GET  /api/documents    → documents.py → mongo_client           │
│  DELETE /api/documents/{id} → documents.py → all 3 DBs          │
│  GET  /health           → main.py  → all service pings          │
└──────┬──────────────┬──────────────────┬────────────────────────┘
       │              │                  │
       ▼              ▼                  ▼
 ┌──────────┐  ┌──────────────┐  ┌─────────────┐
 │  Qdrant  │  │ Elasticsearch│  │   MongoDB   │
 │  Cloud   │  │    Cloud     │  │    Atlas    │
 │ (vectors)│  │  (BM25 text) │  │ (metadata)  │
 └──────────┘  └──────────────┘  └─────────────┘
                                        │
                              ┌─────────────────┐
                              │  Google Gemini  │
                              │  2.5 Flash API  │
                              │  (Liberal mode) │
                              └─────────────────┘
```

---

## 2. Upload & Ingestion Flow

```
User uploads file (PDF / DOCX / TXT)
         │
         ▼
upload.py — validates extension, saves to uploads/, generates document_id (UUID)
         │
         ▼
processor.py — orchestrates the pipeline:
         │
         ├─► extractor.py
         │      PyMuPDF (fast PDF)
         │      → pdfplumber (if PyMuPDF fails)
         │      → Tesseract OCR (if scanned/image PDF)
         │      → python-docx (DOCX)
         │      → plain read (TXT)
         │
         ├─► chunker.py
         │      RecursiveCharacterTextSplitter
         │      chunk_size=512 tokens, chunk_overlap=128
         │      Attaches metadata: {document_id, document_name, chunk_index, total_chunks}
         │
         ├─► embedder.py
         │      BAAI/bge-large-en-v1.5 (local, SentenceTransformers)
         │      Output: 1024-dimensional float vector per chunk
         │
         └─► Storage (parallel):
                ├─ qdrant_client.upsert_vectors()   → Qdrant Cloud ("vectors" collection)
                ├─ mongo_client.insert_chunks()     → MongoDB Atlas ("chunks" collection)
                └─ elastic_client.index_chunks()    → Elastic Cloud ("chunks" index)
```

---

## 3. Query Flow — Both Modes Share Retrieval

```
User submits question + mode ("strict" or "liberal")
         │
         ▼
query.py
  │
  ├─ Meta-query detection: is this a vague query like "explain this document"?
  │     YES → fetch 6× more chunks for broader document coverage
  │
  ├─► retriever.py  [HYBRID SEARCH — runs in parallel]
  │      ├─ BM25 Search:   elastic_client.search() → top-k keyword matches
  │      └─ Vector Search: embed query → qdrant_client.search() → top-k semantic matches
  │         → merge results, remove duplicates, weight scores (BM25 + vector)
  │
  ├─► _apply_filters()
  │      → filter by document_ids if user selected specific docs from library
  │
  ├─► reranker.py
  │      BAAI/bge-reranker-large (cross-encoder)
  │      Scores each chunk against the query for true relevance
  │      Returns top-k re-ranked chunks
  │
  └─► Mode routing:
        STRICT  → strict_mode.py
        LIBERAL → liberal_mode.py
```

---

## 4. Strict Mode Flow

```
strict_mode.py receives reranked chunks
  │
  ├─ Enrich each result:
  │     document_name, page_number, chunk_index, total_chunks
  │     Build "location" string: "Page 5, Section 2 of 12"
  │
  └─► Gemini API: generate_search_keywords()
        Prompt: "Given this query and document content, generate 5 Google search phrases"
        Returns: ["machine learning survey", "neural networks site:arxiv.org", ...]
        → clickable links in frontend open Google Search in new tab

Response:
  {
    "mode": "strict",
    "results": [{text, document_name, page, location, score}, ...],
    "search_keywords": ["...", "...", ...],
    "total_results": N,
    "processing_time_ms": X
  }
```

---

## 5. Liberal Mode Flow

```
liberal_mode.py receives reranked chunks
  │
  ├─ _extract_doc_names() — get list of unique document names from results
  ├─ _format_context()    — format chunks as [Source N: doc.pdf, Page X]\ntext
  ├─ _is_meta_query()     — "explain this document"? → reframe as overview request
  │
  └─► _create_liberal_prompt()
        Injects:
          - Instruction to respond in rich Markdown
          - "Uploaded documents: doc1.pdf, doc2.pdf"
          - Document context excerpts
          - Question (or reframed overview request for meta queries)
        Forces structure:
          **DOCUMENT-BASED ANSWER:** ... --- **ADDITIONAL EXPLANATION:** ...
  │
  └─► Gemini 2.5 Flash API call
        → raw Markdown response
        → _parse_liberal_response() splits on "---" separator
  │
  Response:
  {
    "answer": {
      "document_based": "...",        ← rendered as Markdown in browser
      "additional_explanation": "...", ← rendered as Markdown in browser
      "citations": [{document_name, page, chunk_text}, ...]
    },
    "metadata": {processing_time_ms, llm_model}
  }
```

---

## 6. Document Management Flow

```
Frontend Document Library:
  ├─ On load → GET /api/documents → list all unique docs from MongoDB
  ├─ Checkbox per doc → user selects which docs to search
  ├─ "Select All" / "None" toggles
  └─ Delete button → DELETE /api/documents/{id}
                         ├─ MongoDB:       delete_many({metadata.document_id: id})
                         ├─ Qdrant:        delete by payload filter (document_id == id)
                         └─ Elasticsearch: delete_by_query (metadata.document_id.keyword: id)

Query with filter:
  - If user selected subset → payload.document_ids = [id1, id2, ...]
  - _apply_filters() removes chunks not in selected set before reranking
```

---

## 7. Configuration (.env Variables)

```env
# Databases
MONGO_URI=mongodb+srv://...          # MongoDB Atlas SRV connection
ES_URL=https://...elastic-cloud...   # Elastic Cloud endpoint
ES_API_KEY=...                       # Elastic API key (Base64)
QDRANT_URL=https://...qdrant.io      # Qdrant Cloud endpoint
QDRANT_API_KEY=...                   # Qdrant API key

# LLM
LLM_PROVIDER=gemini                  # Options: gemini | groq | ollama
GEMINI_API_KEY=AIza...               # Google AI Studio key
GEMINI_MODEL=gemini-2.5-flash        # Model to use

# Ollama (local fallback, optional)
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
LLM_MODEL=llama3:8b
```

---

## 8. Key Files Reference

| File | Role |
|------|------|
| `backend/main.py` | FastAPI app, CORS, router registration, health endpoint |
| `backend/config.py` | Loads all .env variables, typed settings object |
| `backend/routers/upload.py` | File upload endpoint |
| `backend/routers/query.py` | Query routing: meta detection, retrieval, mode branching |
| `backend/routers/documents.py` | Document list + delete API |
| `backend/services/processor.py` | Ingestion pipeline orchestrator |
| `backend/services/extractor.py` | PDF/DOCX/TXT text extraction with OCR fallback |
| `backend/services/chunker.py` | Text splitting with metadata attachment |
| `backend/services/embedder.py` | BGE embedding model wrapper |
| `backend/services/retriever.py` | Hybrid BM25 + vector search |
| `backend/services/reranker.py` | Cross-encoder reranking |
| `backend/services/strict_mode.py` | Location enrichment + Gemini search keywords |
| `backend/services/liberal_mode.py` | Gemini LLM integration, meta-query detection, Markdown prompts |
| `backend/db/qdrant_client.py` | Qdrant: upsert, search, delete by document |
| `backend/db/mongo_client.py` | MongoDB: insert, list, delete documents |
| `backend/db/elastic_client.py` | Elasticsearch: index, search, delete by document |
| `frontend/index.html` | Entire UI: upload, document library, query, results |