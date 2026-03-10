from fastmcp import FastMCP

from kluky_mcp.models import NewSessionInput


def register(mcp: FastMCP) -> None:
    """Register UC0 tools."""

    @mcp.tool(name="new_session")
    def new_session(params: NewSessionInput) -> str:
        """Clear the current conversation and start a new session."""
        return "new_session"
