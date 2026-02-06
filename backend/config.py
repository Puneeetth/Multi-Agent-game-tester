"""
Configuration settings for the Multi-Agent Game Tester
"""
import os
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Multi-Agent Game Tester"
    DEBUG: bool = True
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    ARTIFACTS_DIR: Path = BASE_DIR / "artifacts"
    REPORTS_DIR: Path = BASE_DIR / "reports"
    RAG_DIR: Path = BASE_DIR / "rag_data"
    
    # Ollama settings
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llava"
    OLLAMA_TEXT_MODEL: str = "llama3.2"
    
    # Browser settings
    BROWSER_HEADLESS: bool = False
    BROWSER_TIMEOUT: int = 30000  # ms
    
    # Test settings
    MIN_TEST_CASES: int = 20
    TOP_TEST_CASES: int = 10
    REPEAT_VALIDATION_COUNT: int = 3
    
    # ChromaDB
    CHROMA_COLLECTION: str = "game_patterns"
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

# Ensure directories exist
settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.RAG_DIR.mkdir(parents=True, exist_ok=True)
