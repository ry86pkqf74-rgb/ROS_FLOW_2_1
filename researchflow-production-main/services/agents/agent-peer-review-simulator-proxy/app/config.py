"""Configuration for Peer Review Simulator Agent Proxy"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Service settings loaded from environment"""
    
    # LangSmith configuration
    langsmith_api_key: str = ""
    langsmith_agent_id: str = ""
    langsmith_api_url: str = "https://api.smith.langchain.com/v1"
    langsmith_timeout_seconds: int = 600  # 10 minutes for comprehensive reviews
    
    # Service configuration
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
