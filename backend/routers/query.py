from fastapi import APIRouter, HTTPException
import time
from typing import List, Optional
from ..models.schemas import QueryRequest, QueryResponse, SearchResult
from ..services.retriever import Retriever
from ..services.reranker import Reranker
from ..config import config

router = APIRouter()

# These will be initialized on first use
_retriever: Optional[Retriever] = None
_reranker: Optional[Reranker] = None

def get_retriever_and_reranker():
    global _retriever, _reranker
    if _retriever is None or _reranker is None:
        try:
            _retriever = Retriever()
            _reranker = Reranker()
        except Exception as e:
            # Log the error (in a real app, you'd use proper logging)
            print(f"Failed to initialize retriever or reranker: {e}")
            raise HTTPException(
                status_code=503,
                detail="Service unavailable: Could not connect to required services (Elasticsearch, Qdrant) or load models."
            )
    return _retriever, _reranker

@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query documents using hybrid retrieval and re-ranking.

    Args:
        request: Query request containing question and optional filters

    Returns:
        Query response with ranked results
    """
    start_time = time.time()

    try:
        retriever, reranker = get_retriever_and_reranker()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )

    try:
        # Perform initial retrieval based on mode
        if request.mode == "bm25":
            initial_results = retriever.bm25_search(
                query_text=request.question,
                limit=request.limit * 2  # Get more for re-ranking
            )
        elif request.mode == "vector":
            initial_results = retriever.vector_search(
                query_text=request.question,
                limit=request.limit * 2  # Get more for re-ranking
            )
        else:  # hybrid mode (default)
            initial_results = retriever.hybrid_search(
                query_text=request.question,
                limit=request.limit * 2  # Get more for re-ranking
            )

        # Apply filters if specified (basic implementation)
        filtered_results = initial_results
        if request.document_ids:
            filtered_results = [
                r for r in filtered_results
                if r["metadata"].get("document_id") in request.document_ids
            ]

        if request.domain:
            filtered_results = [
                r for r in filtered_results
                if r["metadata"].get("domain") == request.domain
            ]

        # Re-rank the results
        if filtered_results:
            reranked_results = reranker.rerank(
                query=request.question,
                documents=filtered_results,
                top_k=request.limit
            )
        else:
            reranked_results = []

        # Convert to SearchResult objects
        search_results = []
        for result in reranked_results:
            search_results.append(
                SearchResult(
                    id=result["id"],
                    score=result.get("score", 0.0),
                    text=result["text"],
                    metadata=result["metadata"],
                    rerank_score=result.get("rerank_score")
                )
            )

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        return QueryResponse(
            query=request.question,
            results=search_results,
            total_results=len(search_results),
            processing_time_ms=processing_time_ms
        )

    except Exception as e:
        # Log the error (in a real app, you'd use proper logging)
        print(f"Error in query_documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )