"""
Liberal Analysis Mode service for generating educational responses
that combine document evidence with AI-generated explanations.
"""
import logging
import time
import json
from typing import List, Dict, Any, Optional
import requests
from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiberalModeService:
    """Service for handling Liberal Analysis Mode queries."""

    def __init__(
        self,
        ollama_host: Optional[str] = None,
        ollama_port: Optional[int] = None,
        model_name: Optional[str] = None,
    ):
        """
        Initialize the Liberal Mode service.

        Args:
            ollama_host: Ollama host (uses config if None)
            ollama_port: Ollama port (uses config if None)
            model_name: LLM model name (uses config if None)
        """
        self.ollama_host = ollama_host or getattr(config, 'OLLAMA_HOST', 'localhost')
        self.ollama_port = ollama_port or int(getattr(config, 'OLLAMA_PORT', '11434'))
        self.model_name = model_name or getattr(config, 'LLM_MODEL', 'llama3:8b')
        self.ollama_url = f"http://{self.ollama_host}:{self.ollama_port}"

        logger.info(f"Initialized LiberalModeService with Ollama at {self.ollama_url}, model: {self.model_name}")

    def _format_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Format search results into a coherent context block for the LLM.

        Args:
            search_results: List of search results from hybrid search + reranking

        Returns:
            Formatted context string
        """
        if not search_results:
            return "No relevant information found in the uploaded documents."

        context_parts = []
        for i, result in enumerate(search_results, 1):
            # Extract useful metadata for citation
            metadata = result.get("metadata", {})
            doc_name = metadata.get("document_name", "Unknown Document")
            page_num = metadata.get("page_number", "unknown")

            context_part = f"""
[Source {i}: {doc_name}, Page {page_num}]
{result.get('text', '')}
"""
            context_parts.append(context_part.strip())

        return "\n\n---\n\n".join(context_parts)

    def _create_liberal_prompt(self, question: str, context: str) -> str:
        """
        Create the system prompt for Liberal Analysis Mode.

        Args:
            question: User's question
            context: Formatted context from retrieved documents

        Returns:
            Complete prompt for the LLM
        """
        prompt = f"""You are a helpful educational assistant. Your goal is to answer the user's question by combining information from their uploaded documents with your general knowledge to provide a clear, educational response.

PRIORITY: First, answer the user's question using ONLY the provided context from their uploaded documents.

EXPANSION: After providing the document-based answer, add a section titled "Additional Explanation". In this section, use your general knowledge to:
- Simplify complex terms or concepts mentioned in the document-based answer
- Provide analogies or examples to aid understanding
- Give broader context that helps a learner understand the topic better
- Explain related concepts that weren't in the documents but are relevant

CONSTRAINT: Do NOT mix the document-based answer with general knowledge. Keep them strictly separate in your response.

FORMAT YOUR RESPONSE AS FOLLOWS:
DOCUMENT-BASED ANSWER:
[Your answer derived directly from the provided context]

---
ADDITIONAL EXPLANATION:
[Your educational expansions from general knowledge]

CONTEXT FROM UPLOADED DOCUMENTS:
{context}

USER QUESTION: {question}

Remember: The document-based answer must come ONLY from the provided context. The additional explanation can use your general knowledge but should be clearly separated."""

        return prompt

    def _call_ollama(self, prompt: str) -> str:
        """
        Make a call to the Ollama API to generate a response.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Generated text response from the LLM

        Raises:
            ConnectionError: If unable to connect to Ollama
            Exception: For other API errors
        """
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,  # Balanced creativity for educational content
                    "top_p": 0.9,
                }
            }

            logger.info(f"Calling Ollama API at {self.ollama_url}/api/generate")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=30  # 30 second timeout
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API returned status {response.status_code}: {response.text}")

            result = response.json()
            generated_text = result.get("response", "")

            if not generated_text:
                raise Exception("Empty response from Ollama")

            logger.info(f"Received response from Ollama (length: {len(generated_text)} chars)")
            return generated_text.strip()

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Ollama at {self.ollama_url}: {e}")
            raise ConnectionError(f"Unable to connect to Ollama service at {self.ollama_url}. Please ensure Ollama is running and accessible.")
        except requests.exceptions.Timeout as e:
            logger.error(f"Ollama API request timed out: {e}")
            raise Exception("Ollama API request timed out. The model may be taking too long to respond.")
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            raise Exception(f"Failed to generate response from Ollama: {str(e)}")

    def _parse_liberal_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the LLM response to extract document-based answer and additional explanation.

        Args:
            response_text: Raw response text from the LLM

        Returns:
            Dictionary with 'document_based' and 'additional_explanation' keys
        """
        # Initialize default values
        document_based = ""
        additional_explanation = ""

        # Try to split by the marker
        if "---" in response_text:
            parts = response_text.split("---", 1)
            if len(parts) == 2:
                # Process first part (should contain document-based answer)
                first_part = parts[0].strip()
                if "DOCUMENT-BASED ANSWER:" in first_part:
                    document_based = first_part.replace("DOCUMENT-BASED ANSWER:", "").strip()
                else:
                    # If no marker found, assume the first part is the document-based answer
                    document_based = first_part

                # Process second part (should contain additional explanation)
                second_part = parts[1].strip()
                if "ADDITIONAL EXPLANATION:" in second_part:
                    additional_explanation = second_part.replace("ADDITIONAL EXPLANATION:", "").strip()
                else:
                    # If no marker found, assume the second part is the additional explanation
                    additional_explanation = second_part
            else:
                # Fallback: treat entire response as document-based
                document_based = response_text
        else:
            # No separator found, check for the section headers
            if "DOCUMENT-BASED ANSWER:" in response_text and "ADDITIONAL EXPLANATION:" in response_text:
                # Split by the section headers
                doc_start = response_text.find("DOCUMENT-BASED ANSWER:")
                add_start = response_text.find("ADDITIONAL EXPLANATION:")

                if doc_start != -1 and add_start != -1 and add_start > doc_start:
                    document_based = response_text[doc_start + len("DOCUMENT-BASED ANSWER:"):add_start].strip()
                    additional_explanation = response_text[add_start + len("ADDITIONAL EXPLANATION:"):].strip()
                else:
                    # Fallback
                    document_based = response_text
            else:
                # No clear separation, treat as document-based answer
                document_based = response_text

        # Clean up any extra whitespace or markers
        document_based = document_based.strip()
        additional_explanation = additional_explanation.strip()

        return {
            "document_based": document_based,
            "additional_explanation": additional_explanation
        }

    def generate_liberal_answer(
        self,
        question: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a liberal mode answer combining document evidence with AI explanations.

        Args:
            question: User's question
            search_results: List of search results from hybrid search + reranking

        Returns:
            Dictionary containing the structured response
        """
        start_time = time.time()

        try:
            # Format context from search results
            context = self._format_context(search_results)

            # Create the prompt for the LLM
            prompt = self._create_liberal_prompt(question, context)

            # Generate response from Ollama
            raw_response = self._call_ollama(prompt)

            # Parse the response into sections
            parsed_response = self._parse_liberal_response(raw_response)

            # Extract citations from search results
            citations = []
            for result in search_results:
                metadata = result.get("metadata", {})
                citation = {
                    "document_name": metadata.get("document_name", "Unknown Document"),
                    "page": metadata.get("page_number", 0),
                    "chunk_text": result.get("text", "")[:200] + "..." if len(result.get("text", "")) > 200 else result.get("text", "")
                }
                citations.append(citation)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Build the final response
            response = {
                "answer": {
                    "document_based": parsed_response["document_based"],
                    "additional_explanation": parsed_response["additional_explanation"],
                    "citations": citations
                },
                "metadata": {
                    "mode": "liberal",
                    "llm_model": self.model_name,
                    "processing_time_ms": round(processing_time * 1000, 2)
                }
            }

            logger.info(f"Generated liberal mode answer in {processing_time:.2f}s")
            return response

        except ConnectionError as e:
            # Handle Ollama connection issues gracefully
            logger.error(f"Ollama connection error: {e}")
            raise ConnectionError(f"Unable to connect to Ollama service: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating liberal mode answer: {e}")
            raise Exception(f"Failed to generate liberal mode answer: {str(e)}")

    def health_check(self) -> bool:
        """
        Check if the Liberal Mode service is healthy (can connect to Ollama).

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Try to connect to Ollama and list models
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LiberalModeService health check failed: {e}")
            return False