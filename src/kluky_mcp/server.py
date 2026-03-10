"""MCP server entrypoint and composition."""

from fastmcp import FastMCP

from kluky_mcp.constants import SERVICE_NAME
from kluky_mcp.tools.health import register as register_health
from kluky_mcp.tools.uc0 import register as register_uc0
from kluky_mcp.tools.uc1 import register as register_uc1
from kluky_mcp.tools.uc2 import register as register_uc2
from kluky_mcp.tools.uc3 import register as register_uc3


def create_server() -> FastMCP:
    """Create and register the Kluky MCP server."""
    mcp = FastMCP(SERVICE_NAME)

    register_health(mcp)
    register_uc0(mcp)
    register_uc1(mcp)
    register_uc2(mcp)
    register_uc3(mcp)

    return mcp


mcp = create_server()


def main() -> None:
    """Run the MCP server over stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
