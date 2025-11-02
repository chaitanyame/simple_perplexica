import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # OpenRouter Configuration
    openrouter_api_key: str
    openrouter_model: str = "deepseek/deepseek-chat-v3.1:free"

    # SerperDev Configuration
    serper_api_key: str

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 3002

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
