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
        "hybrid", description="Search mode: 'bm25', 'vector', or 'hybrid'"
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
    """Response model for query endpoint."""
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time_ms: float