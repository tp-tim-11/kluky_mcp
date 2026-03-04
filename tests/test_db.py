"""Tests for database connection."""

import pytest

from kluky_mcp.db import get_db_connection


def test_db_connection() -> None:
    """Test that database connection can be established."""
    conn = get_db_connection()
    assert conn is not None
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        result = cur.fetchone()
        assert result == (1,)
    conn.close()

def test_db_timezone() -> None:
    """Test that database timezone is set correctly."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SHOW TIME ZONE")
        result = cur.fetchone()
        assert result == ("Europe/Bratislava",)
    conn.close()
