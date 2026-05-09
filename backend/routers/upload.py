from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uuid
import os
import shutil
from pathlib import Path
import logging
from services.processor import process_uploaded_file

router = APIRouter()
logger = logging.getLogger(__name__)

# Directory to store uploaded files
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a document (PDF, DOCX, TXT) for processing.
    Returns a document_id for tracking and processing results.
    """
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".txt"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Generate unique document ID
    document_id = str(uuid.uuid4())

    # Define file path
    file_path = UPLOAD_DIR / f"{document_id}_{file.filename}"

    # Save file to disk
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    finally:
        file.file.close()

    # Process the document through the ingestion pipeline
    try:
        # Determine domain from filename or content? For now, default to "unknown"
        # In a real system, we might use file content or user input to determine domain.
        domain = "unknown"  # Could be inferred from file path or metadata
        result = process_uploaded_file(
            file_path=str(file_path),
            document_id=document_id,
            document_name=file.filename,
            domain=domain,
        )
    except Exception as e:
        # If processing fails, we still have the file uploaded but mark status as failed
        logger.error(f"Processing failed for document {document_id}: {e}")
        # We could optionally delete the file, but we'll keep it for inspection.
        return JSONResponse(
            status_code=202,  # Accepted but processing failed
            content={
                "document_id": document_id,
                "filename": file.filename,
                "status": "processing_failed",
                "message": f"File uploaded but processing failed: {str(e)}",
            }
        )

    return JSONResponse(
        status_code=200,
        content={
            "document_id": document_id,
            "filename": file.filename,
            "status": "processed",
            "num_chunks": result.get("num_chunks"),
            "message": "File uploaded and successfully processed through ingestion pipeline.",
        }
    )