"""
Elasticsearch client wrapper for BM25 keyword search.
"""
from elasticsearch import Elasticsearch
import logging
import os
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ElasticSearchDB:
    def __init__(self, host: str = "localhost", port: int = 9200):
        self.es = Elasticsearch([f"http://{host}:{port}"])
        logger.info(f"Connected to Elasticsearch at {host}:{port}")

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
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "metadata": {"type": "object"},
                    }
                }
            }
        self.es.indices.create(index=index_name, body=mappings)
        logger.info(f"Created index '{index_name}'.")

    def index_chunk(self, index_name: str, doc_id: str, chunk_text: str, metadata: Dict[str, Any]):
        """
        Index a single chunk document.
        """
        doc = {
            "text": chunk_text,
            "metadata": metadata,
        }
        self.es.index(index=index_name, id=doc_id, body=doc)
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
        search_body = {
            "query": {
                "match": {
                    "text": query_text
                }
            },
            "size": limit
        }
        response = self.es.search(index=index_name, body=search_body)
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