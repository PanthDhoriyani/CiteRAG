"""
Document processing pipeline orchestrator.
Combines extraction, chunking, embedding, and storage.
"""
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any

from .extractor import extract_text
from .chunker import chunk_text_with_metadata
from .embedder import embed_texts
from ..db.qdrant_client import QdrantDB
from ..db.mongo_client import MongoDB
from ..db.elastic_client import ElasticSearchDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        mongo_host: str = "localhost",
        mongo_port: int = 27017,
        mongo_db: str = "rag_platform",
        es_host: str = "localhost",
        es_port: int = 9200,
        collection_name: str = "vectors",
        mongo_collection: str = "chunks",
        es_index: str = "chunks",
    ):
        # Initialize storage clients
        self.qdrant = QdrantDB(host=qdrant_host, port=qdrant_port)
        self.mongo = MongoDB(host=mongo_host, port=mongo_port, db_name=mongo_db)
        self.elastic = ElasticSearchDB(host=es_host, port=es_port)
        self.collection_name = collection_name
        self.mongo_collection = mongo_collection
        self.es_index = es_index

        # Ensure Qdrant collection exists (vector size from BGE large is 1024)
        self.qdrant.create_collection(collection_name, vector_size=1024)
        # Ensure MongoDB collection exists (implicit)
        # Ensure Elasticsearch index exists
        self.elastic.create_index(es_index)

    def process_document(
        self,
        file_path: str,
        document_id: str | None = None,
        document_name: str | None = None,
        domain: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Process a single document through the full pipeline.
        Returns a summary dict.
        """
        if document_id is None:
            document_id = str(uuid.uuid4())
        if document_name is None:
            document_name = Path(file_path).name

        logger.info(f"Processing document: {document_name} (ID: {document_id})")

        # 1. Extract text
        logger.info("Step 1: Extracting text")
        full_text = extract_text(file_path)
        if not full_text.strip():
            raise ValueError("No text extracted from document.")

        # 2. Prepare base metadata for chunks
        base_metadata = {
            "document_id": document_id,
            "document_name": document_name,
            "domain": domain,
            # Note: page_number, paragraph_number, line_start/end would be added per chunk if available.
            # For simplicity, we'll add chunk_index and total_chunks later.
        }

        # 3. Chunk text (with metadata attachment)
        logger.info("Step 2: Chunking text")
        chunked_docs = chunk_text_with_metadata(
            text=full_text,
            base_metadata=base_metadata,
            chunk_size=512,
            chunk_overlap=128,
        )

        # 4. Extract chunk texts for embedding
        chunk_texts = [doc["text"] for doc in chunked_docs]
        logger.info(f"Step 3: Generating embeddings for {len(chunk_texts)} chunks")
        embeddings = embed_texts(chunk_texts)  # Returns numpy array

        # 5. Prepare data for storage
        logger.info("Step 4: Preparing storage payloads")
        qdrant_points = []
        mongo_docs = []
        es_docs = []

        for i, (chunk_doc, embedding) in enumerate(zip(chunked_docs, embeddings)):
            # Create a unique ID for this chunk (could be UUID or based on document and chunk index)
            chunk_id = f"{document_id}_{i}"

            # Qdrant: vector + payload (metadata)
            payload = chunk_doc["metadata"].copy()
            payload["text"] = chunk_doc["text"]  # Also store text in payload for convenience
            qdrant_points.append({
                "id": chunk_id,
                "vector": embedding.tolist(),
                "payload": payload,
            })

            # MongoDB: store chunk text and metadata
            mongo_docs.append({
                "text": chunk_doc["text"],
                "metadata": chunk_doc["metadata"],
            })

            # Elasticsearch: store for BM25
            es_docs.append({
                "text": chunk_doc["text"],
                "metadata": chunk_doc["metadata"],
            })

        # 6. Store in Qdrant
        logger.info("Step 5: Storing vectors in Qdrant")
        self.qdrant.upsert_vectors(
            collection_name=self.collection_name,
            vectors=[p["vector"] for p in qdrant_points],
            payloads=[p["payload"] for p in qdrant_points],
            ids=[p["id"] for p in qdrant_points],
        )

        # 7. Store in MongoDB
        logger.info("Step 6: Storing metadata in MongoDB")
        self.mongo.insert_chunks(
            collection_name=self.mongo_collection,
            chunks=mongo_docs,
        )

        # 8. Store in Elasticsearch
        logger.info("Step 7: Indexing text in Elasticsearch")
        self.elastic.index_chunks(
            index_name=self.es_index,
            chunks=es_docs,
        )

        logger.info(f"Document processing complete. Stored {len(chunk_texts)} chunks.")
        return {
            "document_id": document_id,
            "document_name": document_name,
            "num_chunks": len(chunk_texts),
            "status": "processed",
        }

# Convenience function for external use
def process_uploaded_file(
    file_path: str,
    document_id: str | None = None,
    document_name: str | None = None,
    domain: str = "unknown",
) -> Dict[str, Any]:
    processor = DocumentProcessor()
    return processor.process_document(
        file_path=file_path,
        document_id=document_id,
        document_name=document_name,
        domain=domain,
    )