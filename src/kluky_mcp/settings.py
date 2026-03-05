"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = ""
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str = "postgres"
    db_password: str = ""
    db_sslmode: str = "prefer"
    pageindex_api_key: str = "PAGEINDEX_API_KEY"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


settings = Settings()
