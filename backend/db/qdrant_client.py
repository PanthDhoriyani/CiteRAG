"""
Qdrant client wrapper for vector storage.
Deferred connection: does NOT connect in __init__.
Connection errors are raised on first actual operation.

Supports both local and Qdrant Cloud connections:
  - Local: set QDRANT_HOST / QDRANT_PORT in .env (default: localhost:6333)
  - Cloud: set QDRANT_URL + QDRANT_API_KEY in .env
           QDRANT_URL format: https://abc123.aws.cloud.qdrant.io
"""
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse
import logging
import uuid
from typing import List, Dict, Any, Optional

from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QdrantDB:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        # ── Cloud mode: QDRANT_URL + QDRANT_API_KEY are set ──────────────────
        if config.QDRANT_URL and config.QDRANT_API_KEY:
            self.client = QdrantClient(
                url=config.QDRANT_URL,
                api_key=config.QDRANT_API_KEY,
                timeout=10,
            )
            self._connection_label = config.QDRANT_URL
            logger.info(f"QdrantDB configured for Qdrant Cloud: {config.QDRANT_URL}")

        # ── Local mode: host:port ─────────────────────────────────────────────
        else:
            self.host = host if host is not None else config.QDRANT_HOST
            self.port = port if port is not None else config.QDRANT_PORT
            self.client = QdrantClient(host=self.host, port=self.port, timeout=5)
            self._connection_label = f"{self.host}:{self.port}"
            logger.info(f"QdrantDB configured for {self._connection_label} (connection deferred)")

    def _ensure_connected(self):
        """Raise a clear error if Qdrant is not reachable."""
        try:
            self.client.get_collections()
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Qdrant at {self._connection_label}: {e}. "
                "Check QDRANT_URL/QDRANT_API_KEY in .env, or start locally: docker-compose up -d qdrant"
            ) from e

    @staticmethod
    def _to_qdrant_id(raw_id: str) -> str:
        """
        Qdrant point IDs must be either unsigned integers or valid UUIDs.
        Converts any string (e.g. 'docid_0') into a deterministic UUID v5.
        """
        try:
            # If it's already a valid UUID, use it as-is
            uuid.UUID(raw_id)
            return raw_id
        except ValueError:
            # Generate a deterministic UUID from the raw string
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_id))

    def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1024,
        distance: Distance = Distance.COSINE,
    ):
        """Create a collection if it doesn't exist."""
        self._ensure_connected()
        try:
            self.client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' already exists.")
        except Exception:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance),
            )
            logger.info(f"Created collection '{collection_name}' with vector size {vector_size}.")

    def upsert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: List[str] = None,
    ):
        """
        Insert or update vectors with payloads.
        All IDs are normalised to valid Qdrant UUIDs before upserting.
        """
        self._ensure_connected()
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]

        # Normalise to valid Qdrant point IDs
        normalised_ids = [self._to_qdrant_id(i) for i in ids]

        points = [
            PointStruct(id=qid, vector=vec, payload=payload)
            for qid, vec, payload in zip(normalised_ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=collection_name, points=points)
        logger.info(f"Upserted {len(points)} vectors into collection '{collection_name}'.")

    def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        document_ids: Optional[List[str]] = None,
    ):
        """
        Search for similar vectors.
        Returns list of {id, score, payload}.
        Optionally restricts results to specific document_ids (pre-filter at DB level).
        """
        from qdrant_client.http.models import Filter, FieldCondition, MatchAny
        self._ensure_connected()

        query_filter = None
        if document_ids:
            query_filter = Filter(
                must=[FieldCondition(
                    key="document_id",
                    match=MatchAny(any=document_ids),
                )]
            )

        try:
            hits = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )
        except UnexpectedResponse as e:
            if "doesn't exist" in str(e) or "Not found" in str(e):
                logger.warning(f"Collection '{collection_name}' not found. No documents indexed yet.")
                return []
            raise

        results = []
        for hit in hits:
            results.append({
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload,
            })
        logger.info(f"Qdrant search returned {len(results)} results from '{collection_name}'.")
        return results

    def health_check(self) -> bool:
        """Check if the connection to Qdrant is healthy."""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    def delete_by_document_id(self, collection_name: str, document_id: str) -> None:
        """Delete all vectors whose payload.document_id matches the given document_id."""
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue, FilterSelector
        self._ensure_connected()
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",          # top-level in payload (set by processor)
                                match=MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Deleted Qdrant vectors for document '{document_id}' from '{collection_name}'")
        except Exception as e:
            logger.error(f"Qdrant delete_by_document_id failed: {e}")
            raise