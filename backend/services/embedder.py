"""
Embedding generation service using sentence-transformers.
Uses the model specified in config (EMBEDDING_MODEL env var).
"""
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load model once (singleton pattern — lazy, first call only)
_model = None
_loaded_model_name = None


def get_model(model_name: str = None) -> SentenceTransformer:
    global _model, _loaded_model_name
    if model_name is None:
        model_name = config.EMBEDDING_MODEL   # reads from .env / Config
    if _model is None or _loaded_model_name != model_name:
        logger.info(f"Loading embedding model: {model_name}")
        _model = SentenceTransformer(model_name)
        _loaded_model_name = model_name
        logger.info(f"Embedding model loaded (dim={_model.get_sentence_embedding_dimension()})")
    return _model


def embed_texts(texts: list, model_name: str = None) -> np.ndarray:
    """
    Generate embeddings for a list of text strings.
    Returns a numpy array of shape (len(texts), embedding_dim).
    """
    model = get_model(model_name)
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    logger.info(f"Generated embeddings for {len(texts)} texts, shape: {embeddings.shape}")
    return embeddings


def embed_query(text: str, model_name: str = None) -> np.ndarray:
    """
    Generate embedding for a single query text.
    Returns a 1-D numpy array (embedding vector).
    """
    embeddings = embed_texts([text], model_name=model_name)
    return embeddings[0]