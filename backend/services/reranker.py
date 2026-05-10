"""
Re-ranking service using cross-encoder models for improved search precision.
"""
import logging
from typing import List, Dict, Any, Tuple
from sentence_transformers import CrossEncoder
import numpy as np

from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Reranker:
    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-large",
        use_fp16: bool = True,
    ):
        """
        Initialize the re-ranking model.

        Args:
            model_name: Name of the cross-encoder model to use
            use_fp16: Whether to use FP16 for faster inference (if supported)
        """
        self.model_name = model_name
        self.use_fp16 = use_fp16

        try:
            logger.info(f"Loading re-ranking model: {model_name}")
            self.model = CrossEncoder(model_name)
            logger.info(f"Successfully loaded re-ranking model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load re-ranking model {model_name}: {e}")
            raise

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Re-rank documents based on their relevance to the query.

        Args:
            query: The search query
            documents: List of documents to re-rank (each should have 'text' field)
            top_k: Number of top documents to return after re-ranking

        Returns:
            List of documents sorted by relevance score (highest first)
        """
        if not documents:
            return []

        try:
            # Prepare pairs of (query, document_text) for the cross-encoder
            pairs = [(query, doc["text"]) for doc in documents]

            # Get relevance scores from the cross-encoder
            # The CrossEncoder.predict method returns similarity scores
            scores = self.model.predict(pairs, show_progress_bar=False)

            # Add scores to documents
            scored_docs = []
            for doc, score in zip(documents, scores):
                doc_copy = doc.copy()
                doc_copy["rerank_score"] = float(score)  # Ensure it's a Python float
                scored_docs.append(doc_copy)

            # Sort by re-rank score descending
            scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)

            # Return top_k results
            top_docs = scored_docs[:top_k]

            logger.info(f"Re-ranked {len(documents)} documents, returning top {len(top_docs)}")
            return top_docs
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            # Return original documents sorted by their existing score if available
            # or just return the original documents
            if documents and "score" in documents[0]:
                sorted_docs = sorted(documents, key=lambda x: x["score"], reverse=True)
                return sorted_docs[:top_k]
            return documents[:top_k]

    def rerank_with_scores(
        self,
        query: str,
        documents: List[Dict[str, Any]],
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Re-rank documents and return both documents and their scores.

        Args:
            query: The search query
            documents: List of documents to re-rank (each should have 'text' field)

        Returns:
            List of tuples (document, score) sorted by score descending
        """
        if not documents:
            return []

        try:
            # Prepare pairs of (query, document_text) for the cross-encoder
            pairs = [(query, doc["text"]) for doc in documents]

            # Get relevance scores from the cross-encoder
            scores = self.model.predict(pairs, show_progress_bar=False)

            # Create list of (document, score) tuples
            doc_score_pairs = list(zip(documents, scores))

            # Sort by score descending
            doc_score_pairs.sort(key=lambda x: x[1], reverse=True)

            logger.info(f"Re-ranked {len(documents)} documents with scores")
            return doc_score_pairs
        except Exception as e:
            logger.error(f"Re-ranking with scores failed: {e}")
            # Fallback to original order
            return [(doc, 0.0) for doc in documents]

    def health_check(self) -> bool:
        """
        Check if the re-ranking model is loaded and functional.

        Returns:
            True if the model is ready, False otherwise
        """
        try:
            # Test with a simple example
            test_pairs = [("test query", "test document")]
            _ = self.model.predict(test_pairs, show_progress_bar=False)
            return True
        except Exception as e:
            logger.error(f"Re-ranker health check failed: {e}")
            return False