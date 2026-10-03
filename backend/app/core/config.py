"""Application settings, read from the environment (and a repo-level .env in development).

Every variable here is documented in .env.example. Secrets are never given defaults.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DataMode = Literal["synthetic", "real"]
LlmProvider = Literal["fake", "ollama", "openai_compat", "hosted"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
        case_sensitive=False,
    )

    # data safety: real forbids any hosted LLM provider (rule 7)
    data_mode: DataMode = "synthetic"

    # LLM layer. FakeLLM is the default until a real dev model is chosen (decision C3)
    llm_provider: LlmProvider = "fake"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = ""
    llm_embed_model: str = ""
    allow_hosted_llm: bool = False

    # storage
    database_url: str = "postgresql+psycopg://edss:edss@localhost:5432/edss"

    # connector
    mcp_connector_url: str = "http://localhost:8765/mcp"
    mcp_connector_token: SecretStr | None = None

    # auth
    jwt_secret: SecretStr | None = None

    # pipeline behaviour
    max_attempts: int = 3
    stale_after_days: int = 90

    # never send run data to external tracing. Enforced at startup, see core/tracing.py
    langchain_tracing_v2: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
