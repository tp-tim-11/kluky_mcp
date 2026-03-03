from fastmcp import FastMCP
from enum import Enum


class Status(Enum):
    IN_PLACE = 1
    LOANED = 2


mcp = FastMCP("Kluky MCP")


@mcp.tool
def list_tools() -> list[str]:
    return list("not implemented")


@mcp.tool
def find_tool(tool_name: str) -> str:
    return "not implemented"


@mcp.tool
def show_tool_position(sector: str, x: int, y: int) -> str:
    return "not implemented"


@mcp.tool
def change_tool_status(tool_name: str, status: Status, name_of_person: str) -> str:
    return "not implemented"


@mcp.tool
def get_documents() -> dict[str, str]:
    return {"not implemented": "true"}


def main():
    print("Hello from kluky-mcp!")


if __name__ == "__main__":
    main()
