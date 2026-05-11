"""
Elasticsearch client wrapper for BM25 keyword search.
"""
from elasticsearch import Elasticsearch
import logging
import os
from typing import List, Dict, Any, Optional

from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ElasticSearchDB:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        # Use provided values or fall back to config
        self.host = host if host is not None else config.ES_HOST
        self.port = port if port is not None else config.ES_PORT

        try:
            self.es = Elasticsearch([f"http://{self.host}:{self.port}"])
            # Test connection
            if not self.es.ping():
                raise ConnectionError(f"Elasticsearch ping failed at {self.host}:{self.port}")
            logger.info(f"Connected to Elasticsearch at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch at {self.host}:{self.port}: {e}")
            raise

    def create_index(self, index_name: str, mappings: Dict[str, Any] = None):
        """
        Create an index with optional mappings.
        If mappings not provided, use default for text field.
        """
        if self.es.indices.exists(index=index_name):
            logger.info(f"Index '{index_name}' already exists.")
            return
        if mappings is None:
            mappings = {
                "properties": {
                    "text": {"type": "text"},
                    "metadata": {"type": "object"},
                }
            }
        # Use the non-deprecated API: pass mappings directly instead of body=
        self.es.indices.create(index=index_name, mappings=mappings)
        logger.info(f"Created index '{index_name}'.")

    def index_chunk(self, index_name: str, doc_id: str, chunk_text: str, metadata: Dict[str, Any]):
        """
        Index a single chunk document.
        """
        doc = {
            "text": chunk_text,
            "metadata": metadata,
        }
        # Use document= instead of deprecated body=
        self.es.index(index=index_name, id=doc_id, document=doc)
        logger.debug(f"Indexed chunk {doc_id} in index '{index_name}'.")

    def index_chunks(self, index_name: str, chunks: List[Dict[str, Any]]):
        """
        Index multiple chunks using the bulk helper for efficiency.
        Each chunk dict should have 'text' and 'metadata'.
        We'll generate IDs based on chunk index or use provided.
        """
        from elasticsearch.helpers import bulk
        actions = []
        for i, chunk in enumerate(chunks):
            doc_id = chunk.get("metadata", {}).get("chunk_id", f"{index_name}_{i}")
            action = {
                "_index": index_name,
                "_id": doc_id,
                "_source": {
                    "text": chunk.get("text"),
                    "metadata": chunk.get("metadata", {}),
                }
            }
            actions.append(action)
        if actions:
            success, _ = bulk(self.es, actions)
            logger.info(f"Indexed {success} chunks into index '{index_name}'.")
        else:
            logger.warning("No chunks to index.")

    def search_text(self, index_name: str, query_text: str, limit: int = 10):
        """
        Perform BM25 keyword search.
        Returns list of matching documents with scores.
        """
        # Use query= and size= instead of deprecated body=
        response = self.es.search(
            index=index_name,
            query={
                "match": {
                    "text": query_text
                }
            },
            size=limit
        )
        hits = response.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            results.append({
                "id": hit["_id"],
                "score": hit["_score"],
                "text": hit["_source"].get("text"),
                "metadata": hit["_source"].get("metadata"),
            })
        logger.info(f"Elasticsearch search returned {len(results)} results for query '{query_text}'.")
        return results

    def health_check(self) -> bool:
        """
        Check if the connection to Elasticsearch is healthy.
        Returns True if healthy, False otherwise.
        """
        try:
            return self.es.ping()
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False