"""
Semantic chunking service with overlap.
Uses LangChain's RecursiveCharacterTextSplitter.
"""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 128,
) -> List[str]:
    """
    Split text into overlapping chunks.
    Returns list of chunk strings.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_text(text)
    logger.info(f"Created {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})")
    return chunks

def chunk_text_with_metadata(
    text: str,
    base_metadata: Dict,
    chunk_size: int = 512,
    chunk_overlap: int = 128,
) -> List[Dict]:
    """
    Split text into chunks and attach metadata to each chunk.
    base_metadata: dict containing document_id, document_name, etc.
    Returns list of dicts, each with 'text' and merged metadata.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_text(text)
    logger.info(f"Created {len(chunks)} chunks with metadata")

    chunked_docs = []
    for i, chunk in enumerate(chunks):
        meta = base_metadata.copy()
        meta.update({
            "chunk_index": i,
            "total_chunks": len(chunks),
            # Note: page/paragraph/line numbers would be added during extraction if available.
            # For simplicity, we leave them as None or default; extraction service should provide.
        })
        chunked_docs.append({
            "text": chunk,
            "metadata": meta
        })
    return chunked_docs