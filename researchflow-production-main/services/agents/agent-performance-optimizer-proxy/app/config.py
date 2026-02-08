"""Configuration for Performance Optimizer Agent Proxy"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuration loaded from environment variables"""
    
    # LangSmith API configuration
    langsmith_api_key: Optional[str] = None
    langsmith_agent_id: str = ""  # LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID
    langsmith_api_url: str = "https://api.smith.langchain.com"
    langsmith_timeout_seconds: int = 300  # 5 minutes default (performance analysis can be slow)
    
    # Logging
    log_level: str = "INFO"
    
    # Google integration (optional - for metrics reading/report writing)
    google_sheets_api_key: Optional[str] = None
    google_docs_api_key: Optional[str] = None
    
    class Config:
        env_prefix = ""
        # Map LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID -> langsmith_agent_id
        fields = {
            'langsmith_agent_id': {
                'env': ['LANGSMITH_PERFORMANCE_OPTIMIZER_AGENT_ID', 'LANGSMITH_AGENT_ID']
            }
        }


settings = Settings()
