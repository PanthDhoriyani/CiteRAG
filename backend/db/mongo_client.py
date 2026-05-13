"""
MongoDB client wrapper for metadata and raw text storage.
Deferred connection: pymongo connects lazily by default.

Supports both local and MongoDB Atlas connections:
  - Local: set MONGO_HOST / MONGO_PORT in .env (default: localhost:27017)
  - Cloud: set MONGO_URI to the full SRV connection string from Atlas
           Format: mongodb+srv://user:password@cluster.mongodb.net/?appName=App
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging
from typing import List, Dict, Any, Optional

from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MongoDB:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db_name: Optional[str] = None,
    ):
        self.db_name = db_name if db_name is not None else config.MONGO_DB_NAME

        # ── Cloud mode: MONGO_URI (Atlas SRV string) is set ──────────────────
        if config.MONGO_URI:
            self.client = MongoClient(
                config.MONGO_URI,
                serverSelectionTimeoutMS=8000,   # Atlas needs a bit more time
            )
            self._connection_label = config.MONGO_URI.split("@")[-1]  # hide password in logs
            logger.info(f"MongoDB configured for Atlas: {self._connection_label}, database '{self.db_name}'")

        # ── Local mode: host:port ─────────────────────────────────────────────
        else:
            self.host = host if host is not None else config.MONGO_HOST
            self.port = port if port is not None else config.MONGO_PORT
            self.client = MongoClient(
                host=self.host,
                port=self.port,
                serverSelectionTimeoutMS=5000,
            )
            self._connection_label = f"{self.host}:{self.port}"
            logger.info(
                f"MongoDB configured for {self._connection_label}, "
                f"database '{self.db_name}' (connection deferred)"
            )

        self.db = self.client[self.db_name]

    def _ensure_connected(self):
        """Raise a clear error if MongoDB is not reachable."""
        try:
            self.client.admin.command("ping")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            raise ConnectionError(
                f"Cannot connect to MongoDB at {self._connection_label}: {e}. "
                "Check MONGO_URI in .env, or run: docker-compose up -d mongo"
            ) from e

    def get_collection(self, collection_name: str):
        """Get a collection, creating it implicitly if it doesn't exist."""
        collection = self.db[collection_name]
        logger.debug(f"Accessed collection '{collection_name}'")
        return collection

    def insert_chunks(self, collection_name: str, chunks: List[Dict[str, Any]]):
        """
        Insert multiple chunk documents.
        Each chunk dict should contain at least 'text' and 'metadata'.
        """
        self._ensure_connected()
        collection = self.get_collection(collection_name)
        documents = [
            {"text": chunk.get("text"), "metadata": chunk.get("metadata", {})}
            for chunk in chunks
        ]
        if documents:
            result = collection.insert_many(documents)
            logger.info(
                f"Inserted {len(result.inserted_ids)} chunks into collection '{collection_name}'."
            )
            return result.inserted_ids
        else:
            logger.warning("No chunks to insert.")
            return []

    def find_chunks(
        self,
        collection_name: str,
        query: Dict[str, Any] = None,
        limit: int = 100,
    ):
        """Find chunks matching query."""
        self._ensure_connected()
        collection = self.get_collection(collection_name)
        if query is None:
            query = {}
        cursor = collection.find(query).limit(limit)
        results = list(cursor)
        logger.info(
            f"Found {len(results)} chunks in collection '{collection_name}' matching query."
        )
        return results

    def health_check(self) -> bool:
        """Check if the connection to MongoDB is healthy."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False

    def list_documents(self, collection_name: str) -> list:
        """
        Return one record per unique document aggregated from chunk records.
        Each record: {document_id, document_name, domain, num_chunks}
        """
        self._ensure_connected()
        collection = self.get_collection(collection_name)
        pipeline = [
            {"$group": {
                "_id": "$metadata.document_id",
                "document_name": {"$first": "$metadata.document_name"},
                "domain": {"$first": "$metadata.domain"},
                "num_chunks": {"$sum": 1},
            }},
            {"$sort": {"document_name": 1}},
        ]
        results = list(collection.aggregate(pipeline))
        # Rename _id → document_id for cleaner API response
        for r in results:
            r["document_id"] = r.pop("_id")
        logger.info(f"Listed {len(results)} unique documents from '{collection_name}'")
        return results

    def delete_document_chunks(self, collection_name: str, document_id: str) -> int:
        """Delete all chunks for a given document_id. Returns number deleted."""
        self._ensure_connected()
        collection = self.get_collection(collection_name)
        result = collection.delete_many({"metadata.document_id": document_id})
        logger.info(
            f"Deleted {result.deleted_count} chunks for document '{document_id}' "
            f"from MongoDB collection '{collection_name}'"
        )
        return result.deleted_count