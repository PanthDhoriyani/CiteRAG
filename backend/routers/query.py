from fastapi import APIRouter

router = APIRouter()

@router.post("/query")
async def query_documents():
    """
    Placeholder for query endpoint.
    Will be implemented in Phase 2.
    """
    return {"message": "Query endpoint not yet implemented"}