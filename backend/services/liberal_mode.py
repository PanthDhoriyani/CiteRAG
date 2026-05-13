"""
Liberal Analysis Mode service for generating educational responses
that combine document evidence with AI-generated explanations.

Supports two LLM backends, controlled by LLM_PROVIDER in .env:
  - 'ollama' (default): local Ollama server at OLLAMA_HOST:OLLAMA_PORT
  - 'groq'            : Groq Cloud API (free) using GROQ_API_KEY
"""
import logging
import time
from typing import List, Dict, Any, Optional
import requests
from ..config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Patterns that indicate the user is asking about the document itself, not specific content
_META_PATTERNS = [
    "explain about this", "explain this document", "explain the document",
    "summarize this", "summarize the document", "summary of this",
    "what is in this", "what is this document", "what does this document",
    "tell me about this document", "describe this document",
    "overview of this", "give me an overview", "about this document",
    "what is this about", "explain about the document", "what are the contents",
    "what topics", "what does it cover", "explain it",
]


def _is_meta_query(question: str) -> bool:
    """Return True if the question is a vague/document-level query rather than topic-specific."""
    q = question.lower().strip()
    return any(pattern in q for pattern in _META_PATTERNS)



class LiberalModeService:
    """Service for handling Liberal Analysis Mode queries."""

    def __init__(
        self,
        ollama_host: Optional[str] = None,
        ollama_port: Optional[int] = None,
        model_name: Optional[str] = None,
    ):
        self.provider = config.LLM_PROVIDER.lower()

        # ── Groq Cloud ────────────────────────────────────────────────────────
        if self.provider == "groq":
            if not config.GROQ_API_KEY:
                raise ValueError(
                    "LLM_PROVIDER=groq but GROQ_API_KEY is not set in .env. "
                    "Get a free key at https://console.groq.com"
                )
            self.groq_api_key = config.GROQ_API_KEY
            self.model_name = model_name or config.GROQ_MODEL
            logger.info(f"LiberalModeService using Groq Cloud, model: {self.model_name}")

        # ── Google Gemini ─────────────────────────────────────────────────────
        elif self.provider == "gemini":
            if not config.GEMINI_API_KEY:
                raise ValueError(
                    "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set in .env. "
                    "Get a free key at https://aistudio.google.com/apikey"
                )
            self.gemini_api_key = config.GEMINI_API_KEY
            self.model_name = model_name or config.GEMINI_MODEL
            logger.info(f"LiberalModeService using Google Gemini, model: {self.model_name}")

        # ── Ollama (local) ────────────────────────────────────────────────────
        else:
            self.ollama_host = ollama_host or config.OLLAMA_HOST
            self.ollama_port = ollama_port or int(config.OLLAMA_PORT)
            self.model_name = model_name or config.LLM_MODEL
            self.ollama_url = f"http://{self.ollama_host}:{self.ollama_port}"
            logger.info(f"LiberalModeService using Ollama at {self.ollama_url}, model: {self.model_name}")

    # ──────────────────────────────────────────────────────────────────────────
    # Context & Prompt Helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _format_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Format search results into a coherent context block for the LLM."""
        if not search_results:
            return "No relevant information found in the uploaded documents."

        context_parts = []
        for i, result in enumerate(search_results, 1):
            metadata = result.get("metadata", {})
            doc_name = metadata.get("document_name", "Unknown Document")
            page_num = metadata.get("page_number", "unknown")
            context_part = f"[Source {i}: {doc_name}, Page {page_num}]\n{result.get('text', '')}"
            context_parts.append(context_part.strip())

        return "\n\n---\n\n".join(context_parts)

    @staticmethod
    def _extract_doc_names(search_results: List[Dict[str, Any]]) -> List[str]:
        """Return a deduplicated list of document names from search results."""
        seen, names = set(), []
        for r in search_results:
            name = r.get("metadata", {}).get("document_name", "")
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        return names

    def _create_liberal_prompt(
        self,
        question: str,
        context: str,
        doc_names: Optional[List[str]] = None,
        is_meta: bool = False,
    ) -> str:
        """Create a structured prompt that instructs Gemini to return rich Markdown."""
        has_context = context and "No relevant information" not in context

        # Build a document list header so Gemini always knows what files are loaded
        doc_list = ""
        if doc_names:
            doc_list = "**Uploaded documents:** " + ", ".join(f"`{d}`" for d in doc_names) + "\n\n"

        if is_meta and doc_names:
            # For vague queries, reframe as an explicit summary/overview request
            reframed = (
                f"Give a comprehensive overview and summary of the following uploaded document(s): "
                f"{', '.join(doc_names)}. "
                f"Explain the main topics, key points, structure, and important findings covered."
            )
            question_block = f"{reframed}\n\n*(Original user query: \"{question}\")*"
        else:
            question_block = question

        if has_context:
            context_note = (
                f"{doc_list}The document excerpts below were retrieved for you. "
                "Use them as your **PRIMARY source**. Ground your answer in these excerpts."
            )
        else:
            context_note = (
                f"{doc_list}⚠️ The uploaded documents have limited extractable text "
                "(possibly image-based or scanned PDFs). "
                "Use your general knowledge to answer comprehensively and note this limitation."
            )

        return f"""You are CiteRAG's educational AI assistant. Answer the user's question in a **well-structured, rich Markdown format**.

## Instructions
- Use **bold** for key terms and important points
- Use `##` and `###` for section headings
- Use bullet points (`-`) or numbered lists for steps, features, or multiple items
- Use `>` blockquotes to highlight important notes or warnings
- Keep paragraphs short and readable
- Separate the document-based answer from your general knowledge expansion clearly

{context_note}

## Response Format (ALWAYS follow this structure)

**DOCUMENT-BASED ANSWER:**
[Answer derived directly from the document excerpts. Cover the key points, topics, and findings found in the documents.]

---

**ADDITIONAL EXPLANATION:**
[Your educational expansion — explain concepts in simple terms, give analogies, examples, advice, or general knowledge. You MAY go beyond the documents here.]

## Context from Uploaded Documents
{context}

## User Question
{question_block}

Now respond in rich Markdown following the format above:"""

    # ──────────────────────────────────────────────────────────────────────────
    # LLM Callers
    # ──────────────────────────────────────────────────────────────────────────

    def _call_groq(self, prompt: str) -> str:
        """Call the Groq Cloud API (OpenAI-compatible chat completions)."""
        try:
            from groq import Groq
            client = Groq(api_key=self.groq_api_key)
            logger.info(f"Calling Groq API, model: {self.model_name}")
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048,
            )
            text = completion.choices[0].message.content
            logger.info(f"Groq response received ({len(text)} chars)")
            return text.strip()
        except ImportError:
            raise RuntimeError(
                "groq package not installed. Run: pip install groq"
            )
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise Exception(f"Groq API call failed: {str(e)}")

    def _call_gemini(self, prompt: str) -> str:
        """Call the Google Gemini API using the new google-genai SDK (free 1M tokens/day)."""
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_api_key)
            logger.info(f"Calling Gemini API, model: {self.model_name}")
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            text = response.text
            logger.info(f"Gemini response received ({len(text)} chars)")
            return text.strip()
        except ImportError:
            raise RuntimeError(
                "google-genai package not installed. Run: pip install google-genai"
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise Exception(f"Gemini API call failed: {str(e)}")

    def _call_ollama(self, prompt: str) -> str:
        """Call the local Ollama API."""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "top_p": 0.9},
            }
            logger.info(f"Calling Ollama API at {self.ollama_url}/api/generate")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60,
            )
            if response.status_code != 200:
                raise Exception(f"Ollama returned status {response.status_code}: {response.text}")
            text = response.json().get("response", "")
            if not text:
                raise Exception("Empty response from Ollama")
            logger.info(f"Ollama response received ({len(text)} chars)")
            return text.strip()
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.ollama_url}. "
                "Install and run Ollama, or set LLM_PROVIDER=groq in .env"
            )
        except requests.exceptions.Timeout:
            raise Exception("Ollama request timed out. Try a smaller model or use LLM_PROVIDER=groq.")
        except Exception as e:
            raise Exception(f"Ollama call failed: {str(e)}")

    def _call_llm(self, prompt: str) -> str:
        """Route to the correct LLM backend based on LLM_PROVIDER."""
        if self.provider == "groq":
            return self._call_groq(prompt)
        elif self.provider == "gemini":
            return self._call_gemini(prompt)
        return self._call_ollama(prompt)

    # ──────────────────────────────────────────────────────────────────────────
    # Response Parser
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_liberal_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the LLM response into document_based and additional_explanation."""
        document_based = ""
        additional_explanation = ""

        if "---" in response_text:
            parts = response_text.split("---", 1)
            first = parts[0].strip()
            second = parts[1].strip()
            document_based = first.replace("DOCUMENT-BASED ANSWER:", "").strip()
            additional_explanation = second.replace("ADDITIONAL EXPLANATION:", "").strip()
        elif "DOCUMENT-BASED ANSWER:" in response_text and "ADDITIONAL EXPLANATION:" in response_text:
            doc_start = response_text.find("DOCUMENT-BASED ANSWER:")
            add_start = response_text.find("ADDITIONAL EXPLANATION:")
            if add_start > doc_start:
                document_based = response_text[doc_start + len("DOCUMENT-BASED ANSWER:"):add_start].strip()
                additional_explanation = response_text[add_start + len("ADDITIONAL EXPLANATION:"):].strip()
            else:
                document_based = response_text
        else:
            document_based = response_text

        return {
            "document_based": document_based.strip(),
            "additional_explanation": additional_explanation.strip(),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Main Public Method
    # ──────────────────────────────────────────────────────────────────────────

    def generate_liberal_answer(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate a liberal mode answer combining document evidence with AI explanations.
        Detects meta/vague queries (e.g. 'explain this document') and reframes them
        as explicit document overview requests so Gemini returns grounded answers.
        Returns a structured response dict.
        """
        start_time = time.time()

        try:
            is_meta = _is_meta_query(question)
            doc_names = self._extract_doc_names(search_results)
            context = self._format_context(search_results)
            prompt = self._create_liberal_prompt(
                question=question,
                context=context,
                doc_names=doc_names,
                is_meta=is_meta,
            )
            if is_meta:
                logger.info(f"Meta query detected: '{question}' — reframing as document overview")
            raw_response = self._call_llm(prompt)
            parsed = self._parse_liberal_response(raw_response)

            citations = []
            for result in search_results:
                metadata = result.get("metadata", {})
                raw_text = result.get("text", "")
                chunk_text = (raw_text[:200] + "...") if len(raw_text) > 200 else raw_text
                citations.append({
                    "document_name": metadata.get("document_name", "Unknown Document"),
                    "page": metadata.get("page_number", 0),
                    "chunk_text": chunk_text,
                })

            processing_time = time.time() - start_time

            return {
                "answer": {
                    "document_based": parsed["document_based"],
                    "additional_explanation": parsed["additional_explanation"],
                    "citations": citations,
                },
                "metadata": {
                    "mode": "liberal",
                    "llm_provider": self.provider,
                    "llm_model": self.model_name,
                    "processing_time_ms": round(processing_time * 1000, 2),
                },
            }

        except (ConnectionError, Exception) as e:
            logger.error(f"Liberal mode error: {e}")
            raise

    def health_check(self) -> bool:
        """Check if the LLM backend is reachable."""
        try:
            if self.provider == "groq":
                from groq import Groq
                Groq(api_key=self.groq_api_key).models.list()
                return True
            elif self.provider == "gemini":
                from google import genai
                client = genai.Client(api_key=self.gemini_api_key)
                # Quick model list to verify key works
                list(client.models.list())
                return True
            else:
                # Ollama: check /api/tags endpoint
                r = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                return r.status_code == 200
        except Exception as e:
            logger.warning(f"LLM health check failed ({self.provider}): {e}")
            return False