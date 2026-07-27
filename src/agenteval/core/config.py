"""Application configuration via pydantic-settings"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = Field(default="AgentEval")
    app_version: str = Field(default="0.1.0")
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=False)

    # Server
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8000)

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://agenteval:agenteval@localhost:5432/agenteval"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # LLM (default for Judge)
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="")
    llm_default_model: str = Field(default="gpt-4o")
    llm_provider: str = Field(default="openai")

    # Logging
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=True)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
