import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Base configuration class with common settings."""

    # API Settings
    PROJECT_NAME: str = "Job Management API"
    PROJECT_DESCRIPTION: str = "A scalable job management system built with FastAPI and GCP services"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    LOG_LEVEL: str = "INFO"
    SHOW_DOCS: bool = True

    # Azure AD Settings
    APP_CLIENT_ID: str
    TENANT_ID: str
    API_SCOPE: str

    # GCP Settings
    PROJECT_ID: str
    LOCATION: str = "us-central1"
    QUEUE_NAME: str
    SERVICE_ACCOUNT_EMAIL: str
    CLOUD_RUN_URL: str

    # MongoDB Settings
    MONGODB_URL: str
    DATABASE_NAME: str = "job_management"
    MONGODB_MAX_CONNECTIONS: int = 100
    MONGODB_MIN_CONNECTIONS: int = 10

    # CORS Settings
    CORS_ORIGINS: list[str] = ["*"]
    CORS_CREDENTIALS: bool = True

    # API Security
    API_KEY_NAME: str = "X-API-Key"
    API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionConfig(BaseConfig):
    """Production configuration."""

    DEBUG: bool = False
    SHOW_DOCS: bool = False
    CORS_ORIGINS: list[str] = []  # Specify allowed origins in production
    

class TestingConfig(BaseConfig):
    """Testing configuration."""

    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    TESTING: bool = True
    MONGODB_URL: str = "mongodb://localhost:27017"


@lru_cache
def get_settings() -> BaseConfig:
    """
    Get cached settings based on environment.
    Uses lru_cache to prevent multiple reads of environment variables.
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    config_type = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig
    }
    return config_type[env]()


# Create settings instance
settings = get_settings()