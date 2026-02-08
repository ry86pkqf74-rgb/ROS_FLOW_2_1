"""Configuration for Results Interpretation Proxy"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Proxy configuration settings"""
    
    # LangSmith Configuration
    langsmith_api_key: str = ""
    langsmith_api_url: str = "https://api.smith.langchain.com/api/v1"
    langsmith_agent_id: str = ""  # Set via env: LANGSMITH_AGENT_ID=<assistant-id>
    langsmith_timeout_seconds: float = 180.0  # 3 minutes for full pipeline
    
    # Logging
    log_level: str = "INFO"
    
    # Optional: LangSmith project for tracing
    langchain_project: str = "researchflow-results-interpretation"
    langchain_tracing_v2: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
