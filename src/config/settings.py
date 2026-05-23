from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    llm_provider: Literal["openai", "qwen", "deepseek"] = "openai"
    llm_api_key: str = Field(default="placeholder", description="LLM API密钥")
    llm_model_name: str = Field(default="gpt-4")
    llm_base_url: str | None = Field(default=None, description="LLM API base URL，DeepSeek/Qwen 兼容 OpenAI 协议时填这里")
    llm_temperature: float = Field(default=0.1, ge=0, le=2)
    llm_max_tokens: int = Field(default=4096, ge=1)

    redis_url: str = Field(default="redis://localhost:6379")
    redis_password: str | None = None

    milvus_url: str = Field(default="localhost:19530")
    milvus_collection: str = Field(default="ecommerce_agent")

    ecommerce_api_url: str = Field(default="http://localhost:9000")
    ecommerce_api_key: str = Field(default="placeholder")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    enable_tracing: bool = True
    prometheus_port: int = Field(default=9090)

    agent_max_iterations: int = Field(default=10, ge=1)
    agent_timeout_seconds: int = Field(default=60, ge=1)
    memory_max_tokens: int = Field(default=2000, ge=100)

    # JWT 认证
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60 * 24)
    auth_enabled: bool = Field(default=False, description="是否启用 JWT 鉴权")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
