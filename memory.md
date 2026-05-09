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