from fastapi import APIRouter, HTTPException
import time
import logging
from typing import List, Optional, Any, Dict
from ..models.schemas import QueryRequest, QueryResponse, SearchResult, LiberalQueryResponse
from ..services.retriever import Retriever
from ..services.reranker import Reranker
from ..services.liberal_mode import LiberalModeService, _is_meta_query
from ..services.strict_mode import build_strict_response

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level singletons — initialised on first use
_retriever: Optional[Retriever] = None
_reranker: Optional[Reranker] = None
_liberal_mode_service: Optional[LiberalModeService] = None


def get_retriever_and_reranker():
    global _retriever, _reranker
    if _retriever is None or _reranker is None:
        try:
            _retriever = Retriever()
            _reranker = Reranker()
        except Exception as e:
            logger.error(f"Failed to initialise retriever or reranker: {e}", exc_info=True)
            _retriever = None
            _reranker = None
            raise HTTPException(
                status_code=503,
                detail="Service unavailable — could not load retrieval models. Make sure all services are running.",
            )
    return _retriever, _reranker


def get_liberal_mode_service():
    global _liberal_mode_service
    if _liberal_mode_service is None:
        try:
            _liberal_mode_service = LiberalModeService()
        except Exception as e:
            logger.error(f"Failed to initialise liberal mode service: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable: could not initialise LLM service — {e}",
            )
    return _liberal_mode_service


@router.post("/query")
async def query_documents(request: QueryRequest) -> Dict[str, Any]:
    """
    Query documents in one of two modes:

    - strict  : Hybrid BM25+vector retrieval, exact document locations
                (page, section), and Gemini-generated Google search keywords.
    - liberal : Hybrid retrieval + Gemini LLM for a full educational answer
                that can also expand beyond the documents.

    Legacy modes bm25 / vector / hybrid are still accepted and route to
    strict internally for backward compatibility.
    """
    start_time = time.time()

    try:
        retriever, reranker = get_retriever_and_reranker()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")

    # Normalise legacy mode names → strict
    effective_mode = request.mode.lower()
    if effective_mode in ("bm25", "vector", "hybrid"):
        effective_mode = "strict"

    try:
        # ── Common retrieval step (both modes) ────────────────────────────────
        # For vague document-level queries, fetch more chunks so the LLM gets
        # a broader picture of the entire document (not just top-k keyword matches)
        is_meta = effective_mode == "liberal" and _is_meta_query(request.question)
        fetch_limit = (request.limit * 6) if is_meta else (request.limit * 2)

        # document_ids pre-filter: pass directly to DB-level search
        # This ensures results always come from selected documents, even if they
        # score lower globally than chunks from other documents.
        initial_results = retriever.hybrid_search(
            query_text=request.question,
            limit=fetch_limit,
            document_ids=request.document_ids or None,
        )

        filtered = _apply_filters(initial_results, request)

        reranked = reranker.rerank(
            query=request.question,
            documents=filtered,
            top_k=request.limit,
        ) if filtered else []

        elapsed_ms = (time.time() - start_time) * 1000

        # ── Liberal mode ──────────────────────────────────────────────────────
        if effective_mode == "liberal":
            liberal_service = get_liberal_mode_service()
            return liberal_service.generate_liberal_answer(
                question=request.question,
                search_results=reranked,
            )

        # ── Strict mode (default) ─────────────────────────────────────────────
        return build_strict_response(
            query=request.question,
            reranked_results=reranked,
            processing_time_ms=elapsed_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in query_documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _apply_filters(results: List[Dict], request: QueryRequest) -> List[Dict]:
    """Apply optional domain filter. document_ids are now handled at DB level."""
    if request.domain:
        results = [
            r for r in results
            if r.get("metadata", {}).get("domain") == request.domain
        ]
    return results