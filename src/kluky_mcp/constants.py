"""Shared constants for the Kluky MCP server."""

SERVICE_NAME = "kluky_mcp"
TOOL_NAMESPACE = ""

CHARACTER_LIMIT = 12_000
NOT_IMPLEMENTED_PREFIX = "NOT_IMPLEMENTED"

API_BASE_URL_ENV = "KLUKY_API_BASE_URL"
API_KEY_ENV = "KLUKY_API_KEY"
REQUEST_TIMEOUT_SECONDS = 30.0


def tool_name(name: str) -> str:
    """Generate tool name with namespace prefix if namespace is not empty."""
    if TOOL_NAMESPACE:
        return f"{TOOL_NAMESPACE}_{name}"
    return name
