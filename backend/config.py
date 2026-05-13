"""
Configuration management for the RAG application.
Loads configuration from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Always load from the project root .env regardless of where uvicorn is started from
_project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=_project_root / ".env", override=False)


class Config:
    """Application configuration class."""

    # Qdrant settings (local fallback)
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

    # MongoDB settings
    MONGO_HOST: str = os.getenv("MONGO_HOST", "localhost")
    MONGO_PORT: int = int(os.getenv("MONGO_PORT", "27017"))
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "rag_platform")

    # Elasticsearch settings (local fallback)
    ES_HOST: str = os.getenv("ES_HOST", "localhost")
    ES_PORT: int = int(os.getenv("ES_PORT", "9200"))

    # ── Cloud overrides ────────────────────────────────────────────────────────
    # MongoDB Atlas: set MONGO_URI to the full SRV connection string.
    # When MONGO_URI is set, MONGO_HOST/MONGO_PORT are ignored by the client.
    # Format: mongodb+srv://user:password@cluster.mongodb.net/?appName=AppName
    MONGO_URI: Optional[str] = os.getenv("MONGO_URI")

    # Application settings
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

    # Embedding model settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")

    # File upload settings
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB

    # Ollama settings
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "localhost")
    OLLAMA_PORT: int = int(os.getenv("OLLAMA_PORT", "11434"))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3:8b")

    # ── Cloud overrides ────────────────────────────────────────────────────────
    # Elasticsearch Cloud Hosted: set ES_URL + (ES_API_KEY or ES_USERNAME/ES_PASSWORD)
    # When ES_URL is set, ES_HOST/ES_PORT are ignored by the client.
    ES_URL: Optional[str] = os.getenv("ES_URL")                 # e.g. https://abc.es.ap-south-1.aws.elastic.co
    ES_API_KEY: Optional[str] = os.getenv("ES_API_KEY")         # preferred: base64 id:secret from Cloud
    ES_USERNAME: Optional[str] = os.getenv("ES_USERNAME")       # fallback: basic auth username (elastic)
    ES_PASSWORD: Optional[str] = os.getenv("ES_PASSWORD")       # fallback: basic auth password

    # Qdrant Cloud: set QDRANT_URL + QDRANT_API_KEY
    # When QDRANT_URL is set, QDRANT_HOST/QDRANT_PORT are ignored by the client.
    QDRANT_URL: Optional[str] = os.getenv("QDRANT_URL")         # e.g. https://abc.aws.cloud.qdrant.io
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY") # API key from Qdrant Cloud dashboard

    # LLM Provider: 'ollama' (local) | 'groq' (cloud) | 'gemini' (Google Cloud — free)
    # Set LLM_PROVIDER and the matching API key to enable cloud LLM.
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")      # which backend to use

    # Groq Cloud (https://console.groq.com — free)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Google Gemini (https://aistudio.google.com/apikey — free 1M tokens/day)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration values."""
        # Validate ports are in valid range
        for port_name in ["QDRANT_PORT", "MONGO_PORT", "ES_PORT", "APP_PORT"]:
            port = getattr(cls, port_name)
            if not (1 <= port <= 65535):
                raise ValueError(f"{port_name} must be between 1 and 65535, got {port}")

        # Validate file size is positive
        if cls.MAX_FILE_SIZE <= 0:
            raise ValueError("MAX_FILE_SIZE must be positive")

        return True


# Create a singleton instance
config = Config()