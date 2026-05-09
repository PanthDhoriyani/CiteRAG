# Phase 1: Document Ingestion Pipeline Specification

## Overview
Build the document processor that extracts, chunks, embeds, and stores all uploaded documents. This phase establishes the foundation for the RAG system by processing documents into searchable chunks with embeddings and metadata.

## Goals
- Accept PDF, DOCX, TXT file uploads
- Extract text using appropriate methods based on file type and content
- Extract metadata for each chunk (page, paragraph, document info)
- Perform semantic chunking with overlap to preserve context
- Generate embeddings using BAAI/bge-large-en-v1.5 model
- Store data in three systems: Qdrant (vectors), MongoDB (metadata/text), Elasticsearch (BM25)

## Detailed Requirements

### 1. File Upload Endpoint (FastAPI)
- **Endpoint**: `POST /api/upload`
- **Accepted formats**: PDF, DOCX, TXT
- **Validation**: File type and size limits
- **Storage**: Save raw file to local uploads directory
- **Response**: Return `{ document_id, status }`
- **Processing**: Trigger ingestion job asynchronously

### 2. Text Extraction
Select extractor based on:
| Condition | Tool |
|-----------|------|
| Standard PDF | PyMuPDF |
| PDF with tables/forms | pdfplumber |
| Scanned/image PDF | Tesseract OCR |
| DOCX file | python-docx |
| TXT file | plain read |

**Rules**:
- Try PyMuPDF first for all PDFs
- If text output is empty or very short (< 50 chars), fall back to Tesseract OCR
- Preserve paragraph boundaries as much as possible

### 3. Metadata Extraction
For each chunk, capture:
```json
{
  "document_id": "uuid",
  "document_name": "filename.pdf",
  "page_number": 4,
  "paragraph_number": 2,
  "line_start": 12,
  "line_end": 18,
  "upload_timestamp": "ISO timestamp",
  "domain": "research|legal|healthcare|technical|compliance|education",
  "chunk_index": 0,
  "total_chunks": 42
}
```

### 4. Semantic Chunking
- **Chunk size**: 512 tokens
- **Overlap**: 128 tokens (25% overlap)
- **Method**: LangChain's RecursiveCharacterTextSplitter
- **Requirement**: Maintain metadata linkage per chunk

### 5. Embedding Generation
- **Model**: BAAI/bge-large-en-v1.5 (via sentence-transformers)
- **Output**: 1024-dimensional vector per chunk
- **Implementation**: 
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-large-en-v1.5")
embedding = model.encode(chunk_text)
```

### 6. Storage Systems

#### Qdrant (Vector Store)
- Store: embedding vector + metadata payload
- Collection strategy: One collection per domain OR per document
- Similarity: Cosine similarity

#### MongoDB (Metadata + Raw Text)
- Store: full chunk text + all metadata
- Indexes: document_id, domain, page_number
- Purpose: citation retrieval, audit trail

#### Elasticsearch (BM25 Index)
- Index: chunk_text with standard analyzer
- Fields: chunk_text, document_name
- Purpose: exact keyword match retrieval

## Technical Dependencies
- Python packages: fastapi, uvicorn, python-multipart, pymupdf, pdfplumber, pytesseract, python-docx, sentence-transformers, qdrant-client, pymongo, elasticsearch, langchain
- System dependencies: Tesseract OCR installed

## Success Criteria
All checklist items from project plan must be completed:
- [ ] File upload API endpoint working
- [ ] PyMuPDF extraction working on standard PDFs
- [ ] Tesseract OCR fallback working on scanned PDFs
- [ ] Metadata captured per chunk
- [ ] Chunking with overlap implemented
- [ ] BGE embeddings generated
- [ ] Vectors stored in Qdrant
- [ ] Metadata stored in MongoDB
- [ ] BM25 index populated in Elasticsearch

## Implementation Approach
1. Set up FastAPI project structure
2. Implement file upload endpoint
3. Create text extraction service with fallback logic
4. Implement metadata extraction
5. Add semantic chunking with overlap
6. Integrate embedding generation
7. Set up connections to Qdrant, MongoDB, Elasticsearch
8. Create storage services for each database
9. Wire everything together in the upload processing flow
10. Test with sample documents of each type
