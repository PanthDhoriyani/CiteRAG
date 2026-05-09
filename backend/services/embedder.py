"""
Embedding generation service using sentence-transformers.
Generates embeddings for text chunks.
"""
from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load model once (singleton pattern)
_model = None

def get_model(model_name: str = "BAAI/bge-large-en-v1.5"):
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {model_name}")
        _model = SentenceTransformer(model_name)
    return _model

def embed_texts(texts: list[str], model_name: str = "BAAI/bge-large-en-v1.5") -> np.ndarray:
    """
    Generate embeddings for a list of text strings.
    Returns a numpy array of shape (len(texts), embedding_dim).
    """
    model = get_model(model_name)
    # Encode returns numpy array by default
    embeddings = model.encode(texts, show_progress_bar=False)
    logger.info(f"Generated embeddings for {len(texts)} texts, shape: {embeddings.shape}")
    return embeddings

def embed_query(text: str, model_name: str = "BAAI/bge-large-en-v1.5") -> np.ndarray:
    """
    Generate embedding for a single query text.
    Returns a 1D numpy array (embedding vector).
    """
    embeddings = embed_texts([text], model_name=model_name)
    return embeddings[0]