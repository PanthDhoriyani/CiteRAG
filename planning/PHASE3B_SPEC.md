# Phase 3B: Liberal Analysis Mode Specification

## Overview
Liberal Analysis Mode is designed as an educational assistant. It prioritizes information retrieved from the uploaded documents but allows the LLM to expand upon the answer using its internal general knowledge to provide simplified explanations, context, and analogies.

The core requirement is **Transparency**: The user must always be able to distinguish between what is sourced from their document and what is added by the AI.

## Goals
- Integrate the retrieval pipeline with a local LLM (via Ollama).
- Generate responses that are grounded in document evidence first.
- Implement a "Knowledge Expansion" layer for educational context.
- Ensure a clear structural separation between document-based answers and AI expansions.
- Provide "soft citations" (document name and page number) for the grounded section.

## Detailed Requirements

### 1. LLM Integration (Ollama)
- **Provider:** Ollama (running locally).
- **Default Model:** `llama3:8b` (or as configured in `.env`).
- **Communication:** Use the Ollama API (typically `http://localhost:11434/api/generate` or `/api/chat`).
- **Requirement:** Implementation must handle timeouts and connection errors gracefully.

### 2. Liberal Mode Pipeline Flow
When a user queries in `liberal` mode:
1. **Retrieval:** Trigger the existing Hybrid Retrieval $\rightarrow$ Reranking pipeline.
2. **Context Assembly:** Format the top reranked chunks into a coherent context block.
3. **Prompting:** Pass the context and the user question to the LLM using the **Liberal Mode System Prompt**.
4. **Response Structuring:** Parse the LLM output into two distinct sections.

### 3. System Prompt Design
The prompt must instruct the LLM to act as an educational assistant.

**Prompt Requirements:**
- **Priority:** "Answer the user's question first using ONLY the provided context."
- **Expansion:** "After the primary answer, add a section titled 'Additional Explanation'. In this section, use your general knowledge to simplify complex terms, provide analogies, or give broader context that helps a learner understand the topic."
- **Constraint:** "Do not mix the document-based answer with general knowledge. Keep them strictly separate."
- **Tone:** Educational, helpful, and clear.

### 4. Output Structure
The API must return a structured JSON response so the frontend can render the two sections differently.

**Target Response Schema:**
```json
{
  "answer": {
    "document_based": "The specific answer derived from the chunks...",
    "additional_explanation": "Broad context, analogies, and simplified terms...",
    "citations": [
      {
        "document_name": "manual.pdf",
        "page": 12,
        "chunk_text": "..."
      }
    ]
  },
  "metadata": {
    "mode": "liberal",
    "llm_model": "llama3:8b",
    "processing_time": 1.2
  }
}
```

### 5. New Components to Implement
- **`backend/services/liberal_mode.py`**: 
    - A new service class `LiberalModeService`.
    - Logic to communicate with Ollama.
    - Logic to format the prompt and parse the response.
- **`backend/routers/query.py`**:
    - Update the `/api/query` endpoint to route requests to `LiberalModeService` when `mode == 'liberal'`.

## Technical Dependencies
- **Ollama** installed and running.
- **Model** (e.g., `llama3:8b`) pulled via `ollama pull`.
- **`requests`** or **`httpx`** library for API calls to Ollama.

## Success Criteria
- [ ] LLM successfully generates a response based on provided chunks.
- [ ] Response is clearly split into "Document-Based" and "Additional Explanation" sections.
- [ ] Citations are correctly associated with the document-based part of the answer.
- [ ] The system does not crash if Ollama is offline (returns a clear error).
- [ ] The "Additional Explanation" provides value-add content not present in the raw chunks.
