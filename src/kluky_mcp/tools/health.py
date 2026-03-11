"""Health-check shell tool."""

from fastmcp import FastMCP

from kluky_mcp.constants import NOT_IMPLEMENTED_PREFIX, tool_name
from kluky_mcp.models import HealthCheckInput


def register(mcp: FastMCP) -> None:
    """Register health-check tooling."""

    @mcp.tool(
        name=tool_name("health_check"),
        annotations={
            "title": "Kluky Health Check",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def health_check(params: HealthCheckInput) -> dict[str, str]:
        """Shell placeholder for MCP connectivity checks."""
        return {
            "status": NOT_IMPLEMENTED_PREFIX,
            "tool": tool_name("health_check"),
            "challenge": params.challenge,
        }
