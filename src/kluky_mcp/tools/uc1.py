"""Tool access and position shells."""

from fastmcp import FastMCP

from kluky_mcp.constants import TOOL_NAMESPACE
from kluky_mcp.db import get_db_connection
from kluky_mcp.models import (
    ChangeToolStatusInput,
    ListToolsInput,
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
        """List all available tools from inventory with id, name, status and position."""
        _ = params
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, nazov, pozicia, status, vypozicane_komu
                    FROM resources
                    WHERE deleted = false
                    ORDER BY id
                    """
                )

                rows = cur.fetchall()

                if not rows:
                    return ["No tools found."]

                return [
                    f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | borrowed_by: {r[4] or 'None'}"
                    for r in rows
                ]

        finally:
            conn.close()

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
        """Update tool status and optionally who borrowed it."""
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE resources
                    SET
                        status = %s,
                        vypozicane_komu = CASE
                            WHEN %s = 'borrowed' THEN %s
                            ELSE NULL
                        END
                    WHERE id = %s
                    AND deleted = false
                    """,
                    (
                        params.status,
                        params.status,
                        params.name_of_person,
                        params.tool_name,
                    ),
                )

                if cur.rowcount == 0:
                    return f"Tool '{params.tool_name}' not found."

                conn.commit()

                if params.status == "loaned":
                    return f"Tool '{params.tool_name}' loaned to {params.name_of_person}."
                else:
                    return f"Tool '{params.tool_name}' status changed to '{params.status}'."

        finally:
            conn.close()
