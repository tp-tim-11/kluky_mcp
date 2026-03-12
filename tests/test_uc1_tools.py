"""UC1 integration tests against the real database."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest

from kluky_mcp.db import get_db_connection
from kluky_mcp.models import ChangeToolStatusInput, ListToolsInput, ShowToolPositionInput
from kluky_mcp.tools.uc1 import register as register_uc1
from kluky_mcp.tools.uc1 import translate_status


class _ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, name: str, annotations: dict[str, object]) -> Any:
        _ = annotations

        def decorator(func: Any) -> Any:
            self.tools[name] = func
            return func

        return decorator


@pytest.fixture()
def real_db_connection() -> Iterator[Any]:
    try:
        conn = get_db_connection()
    except Exception as exc:  # pragma: no cover - depends on runner environment
        pytest.skip(f"Real DB is not available: {exc}")

    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def uc1_tools() -> dict[str, Any]:
    registry = _ToolRegistry()
    register_uc1(registry)
    return registry.tools


def test_kluky_list_tools_contract(
    real_db_connection: Any,
    uc1_tools: dict[str, Any],
) -> None:
    """list_tools returns the same non-deleted resources as the live DB query."""
    with real_db_connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, esp, pin, led, status, borrowed_by
            FROM resources
            WHERE deleted = false
            ORDER BY id
            """
        )
        rows = cur.fetchall()

    result = uc1_tools["list_tools"](ListToolsInput())

    if not rows:
        assert result == ["No tools found."]
        return

    expected = [
        (
            f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} "
            f"{translate_status(row[5])} | Vypožičal: {row[6] or '-'}"
        )
        for row in rows
    ]
    assert result == expected


def test_kluky_show_tool_position_rejects_unknown_sector(
    uc1_tools: dict[str, Any],
) -> None:
    """show_tool_position fails fast for sectors outside the configured map."""
    probe = f"Z{uuid4().hex[:4]}"

    result = uc1_tools["show_tool_position"](
        ShowToolPositionInput(sector=probe, pin=1, led=1)
    )

    assert result == "Sector is not in the current ESP sector mapping."



def test_kluky_change_tool_status_persists_and_can_be_restored(
    real_db_connection: Any,
    uc1_tools: dict[str, Any],
) -> None:
    """change_tool_status updates the live DB row and cleanup restores it."""
    with real_db_connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, status, borrowed_by
            FROM resources
            WHERE deleted = false
            ORDER BY id
            LIMIT 1
            """
        )
        row = cur.fetchone()

    if row is None:
        pytest.skip("No non-deleted resource exists in the real DB.")

    resource_id, resource_name, original_status, original_borrowed_by = row
    target_status = "BROKEN" if (original_status or "").upper() != "BROKEN" else "AVAILABLE"

    try:
        result = uc1_tools["change_tool_status"](
            ChangeToolStatusInput(tool_name=str(resource_id), status=target_status)
        )

        assert result == (
            f"Náradie '{resource_id}' - stav: {translate_status(target_status)}."
        )

        with real_db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT status, borrowed_by
                FROM resources
                WHERE id = %s
                """,
                (resource_id,),
            )
            updated = cur.fetchone()

        assert updated == (target_status, None)
    finally:
        with real_db_connection.cursor() as cur:
            cur.execute(
                """
                UPDATE resources
                SET status = %s,
                    borrowed_by = %s
                WHERE id = %s
                """,
                (original_status, original_borrowed_by, resource_id),
            )
        real_db_connection.commit()

        with real_db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT status, borrowed_by, name
                FROM resources
                WHERE id = %s
                """,
                (resource_id,),
            )
            restored = cur.fetchone()

        assert restored == (original_status, original_borrowed_by, resource_name)
