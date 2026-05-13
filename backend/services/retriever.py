"""
Hybrid retrieval service combining BM25 (Elasticsearch) and vector (Qdrant) search.
"""
import logging
from typing import List, Dict, Any, Optional
from ..config import config
from ..db.elastic_client import ElasticSearchDB
from ..db.qdrant_client import QdrantDB
from .embedder import embed_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Retriever:
    def __init__(
        self,
        es_host: Optional[str] = None,
        es_port: Optional[int] = None,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
        index_name: str = "chunks",
        collection_name: str = "vectors",
    ):
        """
        Initialize the hybrid retriever.
        DB connections are deferred — no network calls happen here.
        """
        self.es = ElasticSearchDB(host=es_host, port=es_port)
        self.qdrant = QdrantDB(host=qdrant_host, port=qdrant_port)
        self.index_name = index_name
        self.collection_name = collection_name
        logger.info(
            f"Retriever initialised — ES index '{index_name}', Qdrant collection '{collection_name}'"
        )

    def bm25_search(
        self,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Perform BM25 keyword search using Elasticsearch."""
        try:
            results = self.es.search_text(
                index_name=self.index_name,
                query_text=query_text,
                limit=limit,
            )
            if score_threshold > 0:
                results = [r for r in results if r["score"] >= score_threshold]

            display_q = query_text[:50] + ("..." if len(query_text) > 50 else "")
            logger.info(f"BM25 search returned {len(results)} results for query: '{display_q}'")
            return results
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def vector_search(
        self,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search using Qdrant."""
        try:
            query_embedding = embed_query(query_text)

            results = self.qdrant.search_vectors(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=limit,
                score_threshold=score_threshold,
            )

            # Normalise to the same shape as BM25 results
            formatted = []
            for result in results:
                formatted.append({
                    "id": result["id"],
                    "score": result["score"],
                    "text": result["payload"].get("text", ""),
                    "metadata": result["payload"],
                })

            display_q = query_text[:50] + ("..." if len(query_text) > 50 else "")
            logger.info(f"Vector search returned {len(formatted)} results for query: '{display_q}'")
            return formatted
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def hybrid_search(
        self,
        query_text: str,
        limit: int = 10,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining BM25 and vector search with weighted scoring.
        Falls back gracefully if one source is unavailable.
        """
        bm25_results = self.bm25_search(query_text, limit=limit * 2)
        vector_results = self.vector_search(query_text, limit=limit * 2)

        # Build score lookup dicts
        bm25_scores = {r["id"]: r["score"] for r in bm25_results}
        vector_scores = {r["id"]: r["score"] for r in vector_results}

        # Union of all IDs
        all_ids = set(bm25_scores) | set(vector_scores)

        # Normalise BM25 scores to [0, 1] so they're comparable with vector cosine scores
        max_bm25 = max(bm25_scores.values(), default=1.0) or 1.0

        combined = []
        for doc_id in all_ids:
            norm_bm25 = bm25_scores.get(doc_id, 0.0) / max_bm25
            vec_score = vector_scores.get(doc_id, 0.0)
            combined_score = bm25_weight * norm_bm25 + vector_weight * vec_score

            # Retrieve the full document from whichever source has it
            source = next(
                (r for r in bm25_results if r["id"] == doc_id),
                next((r for r in vector_results if r["id"] == doc_id), None),
            )
            if source is not None:
                combined.append({
                    "id": doc_id,
                    "score": combined_score,
                    "text": source["text"],
                    "metadata": source["metadata"],
                    "bm25_score": bm25_scores.get(doc_id, 0.0),
                    "vector_score": vector_scores.get(doc_id, 0.0),
                })

        combined.sort(key=lambda x: x["score"], reverse=True)

        if score_threshold > 0:
            combined = [r for r in combined if r["score"] >= score_threshold]

        combined = combined[:limit]

        display_q = query_text[:50] + ("..." if len(query_text) > 50 else "")
        logger.info(f"Hybrid search returned {len(combined)} results for query: '{display_q}'")
        return combined

    def health_check(self) -> bool:
        """Check if both Elasticsearch and Qdrant connections are healthy."""
        es_healthy = self.es.health_check()
        qdrant_healthy = self.qdrant.health_check()
        if not es_healthy:
            logger.warning("Elasticsearch health check failed")
        if not qdrant_healthy:
            logger.warning("Qdrant health check failed")
        return es_healthy and qdrant_healthy