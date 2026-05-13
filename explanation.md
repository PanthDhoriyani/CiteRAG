# CiteRAG — Project Explanation

> **What is this?** A smart document Q&A platform. Upload your PDFs, research papers, or legal documents — ask questions — get answers directly from your document with sources and page references. Powered by AI.

---

## 🧠 The Big Idea (In Simple Words)

Imagine you have a 200-page research paper. You don't want to read the whole thing. You just want answers to specific questions like *"What method did they use?"* or *"What were the results?"*

CiteRAG lets you:
1. **Upload** your document (PDF, Word, TXT)
2. **Ask** any question in plain English
3. **Get** a precise answer with the exact page and section it came from

---

## 🏗️ How the Project Works — Step by Step

### Step 1: You Upload a Document

When you upload a file, the system:
1. **Extracts text** from it (even scanned PDFs using OCR)
2. **Splits** the text into small pieces called **chunks** (~512 words each, with 128-word overlap so nothing gets cut off)
3. **Converts** each chunk into a **number vector** (a list of 1024 numbers that represents the meaning of that text) — this is called an **embedding**
4. **Stores** everything in 3 databases simultaneously:
   - 🟢 **Qdrant** — stores the vectors for meaning-based search
   - 🟡 **Elasticsearch** — stores the raw text for keyword-based search
   - 🔵 **MongoDB** — stores document info and metadata

---

### Step 2: You Ask a Question

Your question goes through two searches at the same time:

| Search Type | How it works | Good at |
|-------------|-------------|---------|
| **BM25 (Keyword)** | Like Google — finds exact words | Specific terms, names, numbers |
| **Vector (Semantic)** | Finds chunks with *similar meaning* even if words differ | Concepts, paraphrased questions |

Then the results from both are **merged** and **re-ranked** — a second AI model reads each chunk and scores it based on how well it truly answers your question. The best chunks bubble to the top.

---

### Step 3: You Get the Answer

There are **2 answer modes**:

#### 🔍 Strict Mode
- Shows you the **exact text** from your document that matches your question
- Tells you the **page number** and **section** where it appears
- Generates **Google search keywords** about the topic so you can research further
- 100% grounded in your document — no AI guessing

#### 🎓 Liberal Mode
- Uses **Google Gemini AI** (a powerful language model) to generate a full answer
- Combines what's in your document + general knowledge
- Response is formatted with **headings, bold text, bullet points** for easy reading
- Split into two clear sections:
  - 📄 **Document-Based Answer** — only from your file
  - 🧠 **AI Explanation** — broader context, analogies, advice

---

## 🗄️ The Three Databases — Why Three?

Each database is specialized and does something the others can't:

| Database | Hosted On | Purpose |
|----------|-----------|---------|
| **Qdrant** | Qdrant Cloud (AWS) | Stores 1024-dim vectors. Finds semantically similar chunks even if no keywords match |
| **Elasticsearch** | Elastic Cloud (GCP) | Full-text keyword search using BM25 algorithm. Fast exact matching |
| **MongoDB** | MongoDB Atlas | Stores chunk text + metadata. Powers the document library (list/delete docs) |

Using all three together = **Hybrid Search** = best of keyword + semantic, combined.

---

## 🤖 The AI Stack

| Component | Tool | What it does |
|-----------|------|-------------|
| **Embedding Model** | `BAAI/bge-large-en-v1.5` | Converts text → 1024-dim vectors (runs locally) |
| **Reranker** | `BAAI/bge-reranker-large` | Re-scores retrieved chunks for precision (runs locally) |
| **LLM (Liberal Mode)** | Google Gemini 2.5 Flash | Generates the AI answer (cloud API, free tier) |
| **OCR** | Tesseract | Extracts text from scanned/image PDFs |

---

## 📁 Project Structure (What Each File Does)

```
RAG system/
│
├── backend/                   ← The brain — Python FastAPI server
│   ├── main.py                ← Server entry point, starts everything
│   ├── config.py              ← All settings (API keys, DB URLs) loaded from .env
│   │
│   ├── routers/               ← API endpoints (what the frontend calls)
│   │   ├── upload.py          ← POST /api/upload — receives your file
│   │   ├── query.py           ← POST /api/query — processes your question
│   │   └── documents.py       ← GET/DELETE /api/documents — list & delete docs
│   │
│   ├── services/              ← The actual logic
│   │   ├── processor.py       ← Orchestrates: extract → chunk → embed → store
│   │   ├── extractor.py       ← Pulls text out of PDF/DOCX/TXT files
│   │   ├── chunker.py         ← Splits text into overlapping chunks
│   │   ├── embedder.py        ← Turns chunks into number vectors
│   │   ├── retriever.py       ← Searches Qdrant + Elasticsearch
│   │   ├── reranker.py        ← Re-scores results for relevance
│   │   ├── liberal_mode.py    ← Calls Gemini to generate full AI answers
│   │   └── strict_mode.py     ← Enriches results with location + search keywords
│   │
│   ├── db/                    ← Database connection clients
│   │   ├── qdrant_client.py   ← Talks to Qdrant Cloud
│   │   ├── mongo_client.py    ← Talks to MongoDB Atlas
│   │   └── elastic_client.py  ← Talks to Elastic Cloud
│   │
│   └── models/
│       └── schemas.py         ← Defines what requests/responses look like
│
├── frontend/
│   └── index.html             ← The entire UI (HTML + CSS + JS, single file)
│
├── planning/                  ← Project documentation
│   ├── PROGRESS.md            ← What's done, what's next
│   ├── flow.md                ← Technical flow and architecture
│   └── memory.md              ← Session-by-session change log
│
├── .env                       ← Your secret keys (NEVER committed to GitHub)
├── .env.example               ← Template showing which keys are needed
├── requirements.txt           ← Python packages needed
└── explanation.md             ← This file!
```

---

## ☁️ Cloud Services Used (No Docker Needed!)

All databases are hosted on the cloud — you don't need to run anything locally except the Python backend.

| Service | URL | Free? |
|---------|-----|-------|
| MongoDB Atlas | cloud.mongodb.com | ✅ Free tier |
| Qdrant Cloud | cloud.qdrant.io | ✅ Free tier |
| Elastic Cloud | cloud.elastic.co | ✅ Free trial |
| Google Gemini API | aistudio.google.com | ✅ Free (1M tokens/day) |

---

## 🚀 How to Run the Project

```powershell
# 1. Activate the Python environment
.\venv\Scripts\activate

# 2. Start the backend server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Open the UI in your browser
http://localhost:8000/frontend/index.html
```

**That's it.** No Docker. No local databases. Everything connects to the cloud automatically via your `.env` file.

---

## 📊 Current Status

| Phase | What | Status |
|-------|------|--------|
| Phase 1 | Document upload + processing pipeline | ✅ Complete |
| Phase 2 | Hybrid search + reranking | ✅ Complete |
| Phase 3A | Strict mode (location + keywords) | ✅ Complete |
| Phase 3B | Liberal mode (Gemini AI answers) | ✅ Complete |
| Phase 4 | Full React frontend | ⏳ Next |
| Phase 5 | Production deployment | ⏳ Future |

---

## 🔑 Key Technical Terms (Glossary)

| Term | Simple Explanation |
|------|--------------------|
| **RAG** | Retrieval-Augmented Generation — AI answers grounded in YOUR documents, not just internet knowledge |
| **Embedding** | Converting text into numbers (vectors) so a computer can understand meaning mathematically |
| **BM25** | A keyword search algorithm — similar to how Google matches words |
| **Semantic Search** | Finds similar *meaning* even if the exact words are different |
| **Hybrid Search** | BM25 + Semantic search combined — best of both worlds |
| **Reranking** | A second AI pass that re-orders results by true relevance |
| **Chunk** | A small piece of a document (~512 words) — the unit the system works with |
| **Vector DB** | A database optimized for storing and searching number vectors (embeddings) |
| **LLM** | Large Language Model — AI like Gemini that understands and generates text |
| **OCR** | Optical Character Recognition — reads text from images/scanned PDFs |
