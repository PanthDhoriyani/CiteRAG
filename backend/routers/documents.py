"""
Documents router — list and delete uploaded documents.
GET  /api/documents               → list all documents
DELETE /api/documents/{id}        → delete a document from all DBs
"""
import logging
from fastapi import APIRouter, HTTPException
from ..db.mongo_client import MongoDB
from ..db.qdrant_client import QdrantDB
from ..db.elastic_client import ElasticSearchDB

router = APIRouter()
logger = logging.getLogger(__name__)

MONGO_COLLECTION = "chunks"
QDRANT_COLLECTION = "vectors"
ES_INDEX = "chunks"


@router.get("/documents")
async def list_documents():
    """Return one entry per unique document aggregated from stored chunks."""
    try:
        mongo = MongoDB()
        docs = mongo.list_documents(collection_name=MONGO_COLLECTION)
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        logger.error(f"Failed to list documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not retrieve documents: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and ALL its chunks from MongoDB, Qdrant, and Elasticsearch.
    """
    if not document_id or len(document_id) < 8:
        raise HTTPException(status_code=400, detail="Invalid document_id")

    errors = []

    # 1. Delete from MongoDB
    try:
        mongo = MongoDB()
        mongo_deleted = mongo.delete_document_chunks(MONGO_COLLECTION, document_id)
        logger.info(f"Deleted {mongo_deleted} MongoDB chunks for document {document_id}")
    except Exception as e:
        errors.append(f"MongoDB: {e}")
        logger.error(f"MongoDB delete failed for {document_id}: {e}")
        mongo_deleted = 0

    # 2. Delete from Qdrant
    try:
        qdrant = QdrantDB()
        qdrant.delete_by_document_id(QDRANT_COLLECTION, document_id)
        logger.info(f"Deleted Qdrant vectors for document {document_id}")
    except Exception as e:
        errors.append(f"Qdrant: {e}")
        logger.error(f"Qdrant delete failed for {document_id}: {e}")

    # 3. Delete from Elasticsearch
    try:
        es = ElasticSearchDB()
        es_deleted = es.delete_by_document_id(ES_INDEX, document_id)
        logger.info(f"Deleted {es_deleted} ES docs for document {document_id}")
    except Exception as e:
        errors.append(f"Elasticsearch: {e}")
        logger.error(f"ES delete failed for {document_id}: {e}")
        es_deleted = 0

    if errors and mongo_deleted == 0:
        raise HTTPException(status_code=500, detail=f"Delete failed: {'; '.join(errors)}")

    return {
        "success": True,
        "document_id": document_id,
        "chunks_deleted": mongo_deleted,
        "warnings": errors if errors else None,
    }
