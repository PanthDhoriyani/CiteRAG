"""
Pydantic models for request and response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class QueryRequest(BaseModel):
    """Request model for querying documents."""
    question: str = Field(..., description="The question to ask about the documents")
    document_ids: Optional[List[str]] = Field(
        None, description="Optional list of document IDs to filter by"
    )
    domain: Optional[str] = Field(
        None, description="Optional domain to filter by (e.g., 'research', 'legal')"
    )
    mode: str = Field(
        "hybrid", description="Search mode: 'bm25', 'vector', 'hybrid', or 'liberal'"
    )
    limit: int = Field(
        10, description="Maximum number of results to return", ge=1, le=100
    )


class SearchResult(BaseModel):
    """Model for a single search result."""
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]
    rerank_score: Optional[float] = None


class QueryResponse(BaseModel):
    """Response model for query endpoint (bm25, vector, hybrid modes)."""
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time_ms: float


class LiberalAnswer(BaseModel):
    """Model for the answer portion of liberal mode response."""
    document_based: str
    additional_explanation: str
    citations: List[Dict[str, Any]]


class LiberalQueryResponse(BaseModel):
    """Response model for liberal mode query endpoint."""
    answer: LiberalAnswer
    metadata: Dict[str, Any]