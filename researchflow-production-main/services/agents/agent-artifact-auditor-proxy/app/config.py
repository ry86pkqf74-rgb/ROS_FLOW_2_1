"""Configuration for Artifact Auditor Proxy"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    # LangSmith configuration
    langsmith_api_key: str = ""
    langsmith_agent_id: str = ""  # Assistant ID from LangSmith
    langsmith_api_url: str = "https://api.smith.langchain.com/api/v1"
    langsmith_timeout_seconds: int = 300  # 5 minutes for artifact audits
    
    # Optional LangChain tracing
    langchain_project: str = "researchflow-artifact-auditor"
    langchain_tracing_v2: str = "false"
    
    # Logging
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()
