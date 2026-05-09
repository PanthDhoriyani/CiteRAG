"""
MongoDB client wrapper for metadata and raw text storage.
"""
from pymongo import MongoClient
import logging
import os
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self, host: str = "localhost", port: int = 27017, db_name: str = "rag_platform"):
        self.client = MongoClient(host=host, port=port)
        self.db = self.client[db_name]
        logger.info(f"Connected to MongoDB at {host}:{port}, database '{db_name}'")

    def get_collection(self, collection_name: str):
        """
        Get a collection, creating it implicitly if it doesn't exist.
        """
        collection = self.db[collection_name]
        logger.debug(f"Accessed collection '{collection_name}'")
        return collection

    def insert_chunks(self, collection_name: str, chunks: List[Dict[str, Any]]):
        """
        Insert multiple chunk documents.
        Each chunk dict should contain at least 'text' and 'metadata'.
        """
        collection = self.get_collection(collection_name)
        # Convert each chunk to a document suitable for MongoDB
        documents = []
        for chunk in chunks:
            doc = {
                "text": chunk.get("text"),
                "metadata": chunk.get("metadata", {}),
            }
            documents.append(doc)
        if documents:
            result = collection.insert_many(documents)
            logger.info(f"Inserted {len(result.inserted_ids)} chunks into collection '{collection_name}'.")
            return result.inserted_ids
        else:
            logger.warning("No chunks to insert.")
            return []

    def find_chunks(self, collection_name: str, query: Dict[str, Any] = None, limit: int = 100):
        """
        Find chunks matching query.
        """
        collection = self.get_collection(collection_name)
        if query is None:
            query = {}
        cursor = collection.find(query).limit(limit)
        results = list(cursor)
        logger.info(f"Found {len(results)} chunks in collection '{collection_name}' matching query.")
        return results