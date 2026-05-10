"""
Qdrant client wrapper for vector storage.
"""
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import logging
import os
from typing import List, Dict, Any, Optional

from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QdrantDB:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        # Use provided values or fall back to config
        self.host = host if host is not None else config.QDRANT_HOST
        self.port = port if port is not None else config.QDRANT_PORT

        try:
            self.client = QdrantClient(host=self.host, port=self.port)
            # Test connection
            self.client.get_collections()
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant at {self.host}:{self.port}: {e}")
            raise

    def create_collection(self, collection_name: str, vector_size: int = 1024, distance: Distance = Distance.COSINE):
        """
        Create a collection if it doesn't exist.
        """
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
        ids: List[str] | None = None,
    ):
        """
        Insert or update vectors with payloads.
        If ids are not provided, generates UUID-based IDs.
        """
        if ids is None:
            ids = [str(i) for i in range(len(vectors))]  # Simple fallback; better to use UUIDs
        points = [
            PointStruct(id=idx, vector=vec, payload=payload)
            for idx, vec, payload in zip(ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=collection_name, points=points)
        logger.info(f"Upserted {len(points)} vectors into collection '{collection_name}'.")

    def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
    ):
        """
        Search for similar vectors.
        Returns list of (id, score, payload).
        """
        hits = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )
        results = []
        for hit in hits:
            results.append({
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload,
            })
        logger.info(f"Search returned {len(results)} results from '{collection_name}'.")
        return results

    def health_check(self) -> bool:
        """
        Check if the connection to Qdrant is healthy.
        Returns True if healthy, False otherwise.
        """
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False