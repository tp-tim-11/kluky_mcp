"""Health-check shell tool."""

from fastmcp import FastMCP

from kluky_mcp.constants import NOT_IMPLEMENTED_PREFIX, TOOL_NAMESPACE
from kluky_mcp.models import HealthCheckInput


def register(mcp: FastMCP) -> None:
    """Register health-check tooling."""

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_health_check",
        annotations={
            "title": "Kluky Health Check",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kluky_health_check(params: HealthCheckInput) -> dict[str, str]:
        """Shell placeholder for MCP connectivity checks."""
        return {
            "status": NOT_IMPLEMENTED_PREFIX,
            "tool": "kluky_health_check",
            "challenge": params.challenge,
        }
