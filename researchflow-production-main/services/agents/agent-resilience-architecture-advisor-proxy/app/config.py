"""Configuration settings for Resilience Architecture Advisor Proxy"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # LangSmith Configuration
    langsmith_api_key: str
    langsmith_resilience_architecture_advisor_agent_id: str
    langsmith_api_url: str = "https://api.smith.langchain.com/v1"
    langsmith_timeout_seconds: int = 300
    
    # Service Configuration
    service_name: str = "agent-resilience-architecture-advisor-proxy"
    log_level: str = "INFO"
    
    @property
    def langsmith_agent_id(self) -> str:
        """Alias for the agent ID"""
        return self.langsmith_resilience_architecture_advisor_agent_id


# Global settings instance
settings = Settings()
