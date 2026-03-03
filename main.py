from fastmcp import FastMCP

from tools.health import register as register_health
from tools.uc1 import register as register_uc1
from tools.uc2 import register as register_uc2
from tools.uc3 import register as register_uc3


def create_server() -> FastMCP:
    mcp = FastMCP("Kluky MCP")

    register_health(mcp)
    register_uc1(mcp)
    register_uc2(mcp)
    register_uc3(mcp)

    return mcp


mcp = create_server()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
