"""Application settings."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    db_host: str = ""
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str = "postgres"
    db_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings(
        db_host=os.environ.get("DB_HOST", ""),
        db_port=int(os.environ.get("DB_PORT", 5432)),
        db_name=os.environ.get("DB_NAME", "postgres"),
        db_user=os.environ.get("DB_USER", "postgres"),
        db_password=os.environ.get("DB_PASSWORD", ""),
    )


settings = get_settings()
