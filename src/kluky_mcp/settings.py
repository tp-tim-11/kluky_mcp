"""Application settings."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "aws-1-eu-west-1.pooler.supabase.com"
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str = " postgres.szejlmlpxxinjwgcpqqp "
    db_password: str = ""
    db_sslmode: str = "prefer"
    db_pool_mode: str = "session"

    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OPENAI_API_KEY",
            "openai_api_key",
            "OPEN_AI_API_KEY",
            "open_ai_api_key",
            "CHATGPT_API_KEY",
        ),
    )
    openai_api_base: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OPENAI_API_BASE",
            "openai_api_base",
            "OPEN_AI_API_BASE",
            "open_ai_api_base",
            "OPENAI_BASE_URL",
        ),
    )
    pageindex_model: str = "gpt-4.1-nano-fiit"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent.parent / ".env",
        env_prefix="",
        extra="ignore",
    )


settings = Settings()
