"""Tool access and position shells."""

from fastmcp import FastMCP

from kluky_mcp.constants import TOOL_NAMESPACE
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
        """Shell placeholder for listing inventory tools."""
        _ = params
        return []

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
        """Shell placeholder for finding a tool by name."""
        return format_not_implemented("find_tool", params.model_dump())

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
