"""
Configuration management for Freight Payment AI Assistant
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database Configuration
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI"
    )
    mongodb_database: str = Field(
        default="Ace", 
        description="MongoDB database name"
    )
    mongodb_collection: str = Field(
        default="references",
        description="MongoDB collection name"
    )
    
    # AI/ML Configuration
    voyage_api_key: str = Field(
        default="demo-voyage-key-replace-with-real-key",
        description="VoyageAI API key for embeddings"
    )
    voyage_model: str = Field(
        default="voyage-3-large",
        description="VoyageAI model to use for embeddings"
    )
    vector_dimensions: int = Field(
        default=1024,
        description="Vector dimensions for embeddings"
    )
    vector_index_name: str = Field(
        default="default",
        description="MongoDB Vector Search index name"
    )
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=False, description="API auto-reload in development")
    
    # Security Configuration
    secret_key: str = Field(
        default="your-super-secret-key-change-in-production",
        description="Secret key for JWT tokens"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # Simple caching Configuration  
    cache_ttl: int = Field(
        default=3600,
        description="In-memory cache TTL in seconds"
    )
    
    # Search Configuration
    default_search_limit: int = Field(
        default=10,
        description="Default limit for search results"
    )
    max_search_limit: int = Field(
        default=100,
        description="Maximum limit for search results"
    )
    vector_search_candidates: int = Field(
        default=200,
        description="Number of candidates for vector search"
    )
    
    # Performance Configuration
    batch_size: int = Field(
        default=100,
        description="Batch size for processing operations"
    )
    max_workers: int = Field(
        default=4,
        description="Maximum number of worker threads"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings