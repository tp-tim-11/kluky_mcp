"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "aws-1-eu-west-1.pooler.supabase.com"
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str = " postgres.szejlmlpxxinjwgcpqqp "
    db_password: str = ""
    db_sslmode: str = "prefer"
    db_pool_mode: str = "session"

    open_ai_api_key: str = ""
    open_ai_api_base: str = ""
    pageindex_model: str = "gpt-4.1-nano-fiit"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


settings = Settings()
