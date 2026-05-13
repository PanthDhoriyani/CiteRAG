"""
Elasticsearch client wrapper for BM25 keyword search.
Deferred connection: does NOT connect or ping in __init__.
Connection errors are raised on first actual operation.

Supports both local and Elastic Cloud Hosted connections:
  - Local:  set ES_HOST / ES_PORT in .env (default: localhost:9200)
  - Cloud:  set ES_URL + ES_API_KEY (or ES_USERNAME + ES_PASSWORD) in .env
            ES_URL format: https://abc123.es.ap-south-1.aws.elastic.co
"""
from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import bulk
import logging
from typing import List, Dict, Any, Optional

from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElasticSearchDB:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        # ── Cloud mode: ES_URL is set ─────────────────────────────────────────
        if config.ES_URL:
            kwargs: dict = {
                "hosts": [config.ES_URL],
                "request_timeout": 10,
                "retry_on_timeout": False,
                "max_retries": 0,
            }
            if config.ES_API_KEY:
                # Preferred: API key auth (paste the raw key from Cloud console)
                kwargs["api_key"] = config.ES_API_KEY
                logger.info(f"ElasticSearchDB configured for Elastic Cloud (API key): {config.ES_URL}")
            elif config.ES_USERNAME and config.ES_PASSWORD:
                # Fallback: basic auth (elastic / password shown at deployment creation)
                kwargs["basic_auth"] = (config.ES_USERNAME, config.ES_PASSWORD)
                logger.info(f"ElasticSearchDB configured for Elastic Cloud (basic auth): {config.ES_URL}")
            else:
                logger.warning(
                    "ES_URL is set but no auth credentials found. "
                    "Set ES_API_KEY or both ES_USERNAME and ES_PASSWORD in .env"
                )
            self.es = Elasticsearch(**kwargs)
            self._connection_label = config.ES_URL

        # ── Local mode: host:port ─────────────────────────────────────────────
        else:
            self.host = host if host is not None else config.ES_HOST
            self.port = port if port is not None else config.ES_PORT
            self.es = Elasticsearch(
                [f"http://{self.host}:{self.port}"],
                request_timeout=5,
                retry_on_timeout=False,
                max_retries=0,
            )
            self._connection_label = f"{self.host}:{self.port}"
            logger.info(f"ElasticSearchDB configured for {self._connection_label} (connection deferred)")

    def _ensure_connected(self):
        """Raise a clear error if Elasticsearch is not reachable."""
        try:
            if not self.es.ping():
                raise ConnectionError(
                    f"Elasticsearch ping failed at {self._connection_label}. "
                    "Check your ES_URL / ES_API_KEY in .env, or run: docker-compose up -d elasticsearch"
                )
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Elasticsearch at {self._connection_label}: {e}. "
                "Check your connection settings in .env"
            ) from e

    def create_index(self, index_name: str, mappings: Dict[str, Any] = None):
        """
        Create an index with optional mappings.
        If mappings not provided, use default for text field.
        """
        self._ensure_connected()
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
        self.es.indices.create(index=index_name, mappings=mappings)
        logger.info(f"Created index '{index_name}'.")

    def index_chunk(self, index_name: str, doc_id: str, chunk_text: str, metadata: Dict[str, Any]):
        """Index a single chunk document."""
        self._ensure_connected()
        doc = {
            "text": chunk_text,
            "metadata": metadata,
        }
        self.es.index(index=index_name, id=doc_id, document=doc, refresh="wait_for")
        logger.debug(f"Indexed chunk {doc_id} in index '{index_name}'.")

    def index_chunks(self, index_name: str, chunks: List[Dict[str, Any]]):
        """
        Index multiple chunks using the bulk helper for efficiency.
        Each chunk dict should have 'text' and 'metadata'.
        Uses refresh='wait_for' so documents are immediately searchable after this call.
        """
        self._ensure_connected()
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
            success, failed = bulk(self.es, actions, refresh="wait_for")
            if failed:
                logger.warning(f"Bulk indexing had {len(failed)} failures: {failed[:3]}")
            logger.info(f"Indexed {success} chunks into index '{index_name}'.")
        else:
            logger.warning("No chunks to index.")

    def search_text(self, index_name: str, query_text: str, limit: int = 10):
        """
        Perform BM25 keyword search.
        Returns list of matching documents with scores.
        """
        self._ensure_connected()
        try:
            response = self.es.search(
                index=index_name,
                query={"match": {"text": query_text}},
                size=limit,
            )
        except NotFoundError:
            # Index doesn't exist yet — no documents have been uploaded
            logger.warning(f"Index '{index_name}' not found. No documents indexed yet.")
            return []

        hits = response.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            results.append({
                "id": hit["_id"],
                "score": hit["_score"],
                "text": hit["_source"].get("text"),
                "metadata": hit["_source"].get("metadata"),
            })
        logger.info(f"Elasticsearch search returned {len(results)} results.")
        return results

    def health_check(self) -> bool:
        """
        Check if the connection to Elasticsearch is healthy.
        Returns True if healthy, False otherwise.
        """
        try:
            return self.es.ping(request_timeout=3)
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False

    def delete_by_document_id(self, index_name: str, document_id: str) -> int:
        """
        Delete all documents in the index where metadata.document_id matches.
        Returns the count of deleted documents.
        """
        self._ensure_connected()
        try:
            # Try keyword sub-field first (works when ES dynamic mapping creates .keyword)
            result = self.es.delete_by_query(
                index=index_name,
                body={"query": {"term": {"metadata.document_id.keyword": document_id}}},
                ignore_unavailable=True,
                refresh=True,
            )
            deleted = result.get("deleted", 0)
            if deleted == 0:
                # Fallback: some mappings don't have .keyword sub-field
                result = self.es.delete_by_query(
                    index=index_name,
                    body={"query": {"match_phrase": {"metadata.document_id": document_id}}},
                    ignore_unavailable=True,
                    refresh=True,
                )
                deleted = result.get("deleted", 0)
            logger.info(f"Deleted {deleted} ES docs for document '{document_id}' from index '{index_name}'")
            return deleted
        except NotFoundError:
            logger.warning(f"ES index '{index_name}' not found during delete — nothing to delete")
            return 0
        except Exception as e:
            logger.error(f"ES delete_by_document_id failed: {e}")
            raise