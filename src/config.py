"""
Configuration management for the Policy Intelligence Engine.

Loads settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }
    
    # OpenAI Configuration
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model for reasoning")
    
    # Google Gemini Configuration
    google_api_key: str = Field(default="", description="Google API key for Gemini")
    gemini_model: str = Field(default="gemini-1.5-pro", description="Gemini model for verification")
    
    # Embedding Configuration
    embedding_model: str = Field(
        default="text-embedding-3-small", 
        description="OpenAI embedding model"
    )
    
    # RAG Configuration
    chunk_size: int = Field(default=1000, description="Default chunk size for documents")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks")
    retrieval_top_k: int = Field(default=5, description="Number of chunks to retrieve")
    
    # Confidence Thresholds
    high_confidence_threshold: float = Field(
        default=0.8, 
        description="Threshold for high confidence answers"
    )
    escalation_threshold: float = Field(
        default=0.5, 
        description="Below this threshold, escalate to human"
    )
    
    # Debug
    debug: bool = Field(default=False, description="Enable debug logging")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
