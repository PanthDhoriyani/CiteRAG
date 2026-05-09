"""
Text extraction service for various file types.
Uses PyMuPDF for standard PDFs, pdfplumber for tables/forms,
Tesseract OCR for scanned PDFs, python-docx for DOCX,
and plain read for TXT.
"""
import os
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from docx import Document as DocxDocument
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text(file_path: str) -> str:
    """
    Extract text from a file based on its extension and content.
    Returns extracted text as a string.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext == ".pdf":
        return extract_pdf_text(file_path)
    elif ext == ".docx":
        return extract_docx_text(file_path)
    elif ext == ".txt":
        return extract_txt_text(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF, trying PyMuPDF first, then pdfplumber, then OCR."""
    # Try PyMuPDF
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        if text.strip():
            logger.info(f"Extracted text using PyMuPDF from {file_path}")
            return text
        else:
            logger.warning(f"PyMuPDF returned empty text for {file_path}, trying pdfplumber")
    except Exception as e:
        logger.warning(f"PyMuPDF failed for {file_path}: {e}")

    # Try pdfplumber
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        if text.strip():
            logger.info(f"Extracted text using pdfplumber from {file_path}")
            return text
        else:
            logger.warning(f"pdfplumber returned empty text for {file_path}, trying OCR")
    except Exception as e:
        logger.warning(f"pdfplumber failed for {file_path}: {e}")

    # Fallback to OCR
    logger.info(f"Falling back to OCR for {file_path}")
    return extract_text_with_ocr(file_path)

def extract_text_with_ocr(file_path: str) -> str:
    """Extract text from PDF using OCR (via pdf2image and pytesseract)."""
    try:
        images = convert_from_path(file_path)
        text = ""
        for i, image in enumerate(images):
            # Optionally, preprocess image for better OCR
            text += pytesseract.image_to_string(image)
            if i < len(images) - 1:
                text += "\n"  # Add newline between pages
        logger.info(f"OCR extraction completed for {file_path}")
        return text
    except Exception as e:
        logger.error(f"OCR failed for {file_path}: {e}")
        raise

def extract_docx_text(file_path: str) -> str:
    """Extract text from DOCX file."""
    try:
        doc = DocxDocument(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        logger.info(f"Extracted text from DOCX {file_path}")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX {file_path}: {e}")
        raise

def extract_txt_text(file_path: str) -> str:
    """Extract text from plain TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.info(f"Extracted text from TXT {file_path}")
        return text
    except Exception as e:
        logger.error(f"Failed to read TXT file {file_path}: {e}")
        raise