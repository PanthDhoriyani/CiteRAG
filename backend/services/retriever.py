"""
Hybrid retrieval service combining BM25 (Elasticsearch) and vector (Qdrant) search.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from ..config import config
from ..db.elastic_client import ElasticSearchDB
from ..db.qdrant_client import QdrantDB
from ..services.embedder import embed_query

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

        Args:
            es_host: Elasticsearch host (uses config if None)
            es_port: Elasticsearch port (uses config if None)
            qdrant_host: Qdrant host (uses config if None)
            qdrant_port: Qdrant port (uses config if None)
            index_name: Name of the Elasticsearch index
            collection_name: Name of the Qdrant collection
        """
        self.es = ElasticSearchDB(host=es_host, port=es_port)
        self.qdrant = QdrantDB(host=qdrant_host, port=qdrant_port)
        self.index_name = index_name
        self.collection_name = collection_name

        logger.info(f"Initialized Retriever with index '{index_name}' and collection '{collection_name}'")

    def bm25_search(
        self,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Perform BM25 keyword search using Elasticsearch.

        Args:
            query_text: The search query
            limit: Maximum number of results to return
            score_threshold: Minimum score threshold

        Returns:
            List of search results with id, score, text, and metadata
        """
        try:
            results = self.es.search_text(
                index_name=self.index_name,
                query_text=query_text,
                limit=limit
            )

            # Filter by score threshold if needed
            if score_threshold > 0:
                results = [r for r in results if r["score"] >= score_threshold]

            logger.info(f"BM25 search returned {len(results)} results for query: '{query_text[:50]}...'")
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
        """
        Perform vector similarity search using Qdrant.

        Args:
            query_text: The search query
            limit: Maximum number of results to return
            score_threshold: Minimum score threshold

        Returns:
            List of search results with id, score, text, and metadata
        """
        try:
            # Generate embedding for the query
            query_embedding = embed_query(query_text)

            # Search in Qdrant
            results = self.qdrant.search_vectors(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=limit,
                score_threshold=score_threshold
            )

            # Format results to match BM25 format
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result["id"],
                    "score": result["score"],
                    "text": result["payload"].get("text", ""),
                    "metadata": result["payload"]
                })

            logger.info(f"Vector search returned {len(formatted_results)} results for query: '{query_text[:50]}...'")
            return formatted_results
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
        Perform hybrid search combining BM25 and vector search.

        Args:
            query_text: The search query
            limit: Maximum number of results to return
            bm25_weight: Weight for BM25 scores (0-1)
            vector_weight: Weight for vector scores (0-1)
            score_threshold: Minimum score threshold after weighting

        Returns:
            List of search results sorted by combined score
        """
        # Get results from both search methods
        bm25_results = self.bm25_search(query_text, limit=limit*2)  # Get more to allow for filtering
        vector_results = self.vector_search(query_text, limit=limit*2)

        # Create dictionaries for easy lookup
        bm25_scores = {result["id"]: result["score"] for result in bm25_results}
        vector_scores = {result["id"]: result["score"] for result in vector_results}

        # Get all unique IDs from both result sets
        all_ids = set(bm25_scores.keys()) | set(vector_scores.keys())

        # Combine scores and create combined results
        combined_results = []
        for doc_id in all_ids:
            # Get scores (default to 0 if not found in one of the methods)
            bm25_score = bm25_scores.get(doc_id, 0.0)
            vector_score = vector_scores.get(doc_id, 0.0)

            # Normalize scores to 0-1 range if needed (simple approach)
            # In a more sophisticated implementation, you might use min-max normalization
            # or use the raw scores if they're already comparable

            # Calculate weighted combined score
            combined_score = (bm25_weight * bm25_score) + (vector_weight * vector_score)

            # Find the full result document (prefer BM25 result if available, otherwise vector)
            source_result = None
            for result in bm25_results:
                if result["id"] == doc_id:
                    source_result = result
                    break
            if source_result is None:
                for result in vector_results:
                    if result["id"] == doc_id:
                        source_result = result
                        break

            if source_result is not None:
                combined_results.append({
                    "id": doc_id,
                    "score": combined_score,
                    "text": source_result["text"],
                    "metadata": source_result["metadata"],
                    "bm25_score": bm25_score,
                    "vector_score": vector_score
                })

        # Sort by combined score descending
        combined_results.sort(key=lambda x: x["score"], reverse=True)

        # Apply score threshold
        if score_threshold > 0:
            combined_results = [r for r in combined_results if r["score"] >= score_threshold]

        # Limit results
        combined_results = combined_results[:limit]

        logger.info(f"Hybrid search returned {len(combined_results)} results for query: '{query_text[:50]}...'")
        return combined_results

    def health_check(self) -> bool:
        """
        Check if both Elasticsearch and Qdrant connections are healthy.

        Returns:
            True if both connections are healthy, False otherwise
        """
        es_healthy = self.es.health_check()
        qdrant_healthy = self.qdrant.health_check()

        if not es_healthy:
            logger.warning("Elasticsearch health check failed")
        if not qdrant_healthy:
            logger.warning("Qdrant health check failed")

        return es_healthy and qdrant_healthy