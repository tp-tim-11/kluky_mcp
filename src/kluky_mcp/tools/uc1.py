"""Tool access and position shells."""

from fastmcp import FastMCP

from kluky_mcp.constants import TOOL_NAMESPACE
from kluky_mcp.db import get_db_connection
from kluky_mcp.formatters import format_not_implemented
from kluky_mcp.models import (
    ChangeToolStatusInput,
    FindToolInput,
    ListToolsInput,
    ShowToolPositionInput,
)


def register(mcp: FastMCP) -> None:
    """Register UC1 tools."""

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_list_tools",
        annotations={
            "title": "List Tools",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kluky_list_tools(params: ListToolsInput) -> list[str]:
        """List all available tools from inventory."""
        _ = params
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT nazov FROM resources WHERE deleted = false ORDER BY nazov"
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_find_tool",
        annotations={
            "title": "Find Tool",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kluky_find_tool(params: FindToolInput) -> str:
        """Find a tool by name in the inventory."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, nazov, pozicia, status, vypozicane_komu FROM resources WHERE nazov ILIKE %s AND deleted = false",
                    (f"%{params.tool_name}%",),
                )
                row = cur.fetchone()
                if row is None:
                    return f"Tool '{params.tool_name}' not found."
                return (
                    f"ID: {row[0]}\n"
                    f"Name: {row[1]}\n"
                    f"Position: {row[2]}\n"
                    f"Status: {row[3]}\n"
                    f"Borrowed to: {row[4] or 'N/A'}"
                )
        finally:
            conn.close()

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_show_tool_position",
        annotations={
            "title": "Show Tool Position",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kluky_show_tool_position(params: ShowToolPositionInput) -> str:
        """Shell placeholder for showing tool position by coordinates."""
        return format_not_implemented("show_tool_position", params.model_dump())

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_change_tool_status",
        annotations={
            "title": "Change Tool Status",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    def kluky_change_tool_status(params: ChangeToolStatusInput) -> str:
        """Shell placeholder for updating tool status."""
        return format_not_implemented("change_tool_status", params.model_dump())
