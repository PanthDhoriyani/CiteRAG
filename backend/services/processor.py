"""
Document processing pipeline orchestrator.
Combines extraction, chunking, embedding, and storage.
"""
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .extractor import extract_text
from .chunker import chunk_text_with_metadata
from .embedder import embed_texts
from ..db.qdrant_client import QdrantDB
from ..db.mongo_client import MongoDB
from ..db.elastic_client import ElasticSearchDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project-root-relative upload directory (absolute path so it works regardless of cwd)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
UPLOAD_DIR = _PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


class DocumentProcessor:
    def __init__(
        self,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
        mongo_host: Optional[str] = None,
        mongo_port: Optional[int] = None,
        mongo_db: Optional[str] = None,
        es_host: Optional[str] = None,
        es_port: Optional[int] = None,
        collection_name: str = "vectors",
        mongo_collection: str = "chunks",
        es_index: str = "chunks",
    ):
        # Initialize storage clients (all connections are deferred — no network calls here)
        self.qdrant = QdrantDB(host=qdrant_host, port=qdrant_port)
        self.mongo = MongoDB(host=mongo_host, port=mongo_port, db_name=mongo_db)
        self.elastic = ElasticSearchDB(host=es_host, port=es_port)
        self.collection_name = collection_name
        self.mongo_collection = mongo_collection
        self.es_index = es_index

    def process_document(
        self,
        file_path: str,
        document_id: str = None,
        document_name: str = None,
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
        embeddings = embed_texts(chunk_texts)

        # 5. Prepare data for storage
        logger.info("Step 4: Preparing storage payloads")
        qdrant_points = []
        mongo_docs = []
        es_docs = []

        for i, (chunk_doc, embedding) in enumerate(zip(chunked_docs, embeddings)):
            # Raw chunk ID (used for ES and as the seed for the Qdrant UUID)
            chunk_id = f"{document_id}_{i}"
            # Attach chunk_id to metadata so ES and Qdrant point to the same logical chunk
            chunk_doc["metadata"]["chunk_id"] = chunk_id

            # Qdrant: vector + payload (metadata)
            payload = chunk_doc["metadata"].copy()
            payload["text"] = chunk_doc["text"]
            qdrant_points.append({
                "id": chunk_id,           # QdrantDB._to_qdrant_id() will convert to UUID v5
                "vector": embedding.tolist(),
                "payload": payload,
            })

            # MongoDB: store chunk text and metadata
            mongo_docs.append({
                "text": chunk_doc["text"],
                "metadata": chunk_doc["metadata"],
            })

            # Elasticsearch: store for BM25 (uses chunk_id as _id)
            es_docs.append({
                "text": chunk_doc["text"],
                "metadata": chunk_doc["metadata"],
            })

        # 6. Ensure Qdrant collection exists (vector size from BGE large is 1024)
        logger.info("Step 5: Ensuring Qdrant collection exists")
        self.qdrant.create_collection(self.collection_name, vector_size=1024)

        # 7. Store in Qdrant
        logger.info("Step 6: Storing vectors in Qdrant")
        self.qdrant.upsert_vectors(
            collection_name=self.collection_name,
            vectors=[p["vector"] for p in qdrant_points],
            payloads=[p["payload"] for p in qdrant_points],
            ids=[p["id"] for p in qdrant_points],
        )

        # 8. Store in MongoDB
        logger.info("Step 7: Storing metadata in MongoDB")
        self.mongo.insert_chunks(
            collection_name=self.mongo_collection,
            chunks=mongo_docs,
        )

        # 9. Ensure Elasticsearch index exists, then index
        logger.info("Step 8: Indexing text in Elasticsearch")
        self.elastic.create_index(self.es_index)
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
    document_id: str = None,
    document_name: str = None,
    domain: str = "unknown",
) -> Dict[str, Any]:
    processor = DocumentProcessor()
    return processor.process_document(
        file_path=file_path,
        document_id=document_id,
        document_name=document_name,
        domain=domain,
    )