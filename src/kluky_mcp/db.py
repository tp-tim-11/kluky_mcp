"""Database connection module."""

from collections.abc import Generator
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import connection as PgConnection

from kluky_mcp.settings import settings

print(
    settings.db_host,
    settings.db_name,
    settings.db_user,
    settings.db_password,
    settings.db_port,
    settings.db_sslmode,
)


def get_db_connection() -> PgConnection:
    """Create a database connection using environment variables."""
    if settings.db_sslmode:
        conn = psycopg2.connect(
            host=settings.db_host,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            port=settings.db_port,
            sslmode=settings.db_sslmode,
        )
    else:
        conn = psycopg2.connect(
            host=settings.db_host,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            port=settings.db_port,
        )
    with conn.cursor() as cur:
        cur.execute("SET TIME ZONE 'Europe/Bratislava'")
    return conn


@contextmanager
def get_db_cursor() -> Generator[PgConnection]:
    """Context manager for database cursor."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
