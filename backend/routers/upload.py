from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uuid
import shutil
from pathlib import Path
import logging
from ..services.processor import process_uploaded_file

router = APIRouter()
logger = logging.getLogger(__name__)

# Use an absolute path so it works regardless of the working directory uvicorn is started from
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a document (PDF, DOCX, TXT) for processing.
    Returns a document_id for tracking and processing results.
    """
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".txt"}
    file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    # Generate unique document ID
    document_id = str(uuid.uuid4())

    # Save file to disk
    file_path = UPLOAD_DIR / f"{document_id}_{file.filename}"
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    finally:
        file.file.close()

    logger.info(f"Saved uploaded file to {file_path}")

    # Process the document through the ingestion pipeline
    try:
        domain = "unknown"
        result = process_uploaded_file(
            file_path=str(file_path),
            document_id=document_id,
            document_name=file.filename,
            domain=domain,
        )
    except Exception as e:
        logger.error(f"Processing failed for document {document_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=202,  # Accepted but processing failed
            content={
                "document_id": document_id,
                "filename": file.filename,
                "status": "processing_failed",
                "message": f"File uploaded but processing failed: {str(e)}",
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "document_id": document_id,
            "filename": file.filename,
            "status": "processed",
            "num_chunks": result.get("num_chunks"),
            "message": "File uploaded and successfully processed through ingestion pipeline.",
        },
    )