from functools import lru_cache
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SentinelSafe"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://safety:safety@postgres:5432/safety"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    s3_endpoint_url: str | None = "http://minio:9000"
    s3_bucket: str = "safety-documents"
    s3_access_key_id: str = "minio"
    s3_secret_access_key: str = "miniosecret"
    frontend_origin: AnyHttpUrl | str = "http://localhost:3000"
    ai_provider: str = "rules"
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
