from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool
    def list_tools() -> list[str]:
        """Shell tool placeholder for listing tools from shop inventory."""
        return []

    @mcp.tool
    def find_tool(tool_name: str) -> str:
        """Shell tool placeholder for finding a tool by name."""
        return f"NOT_IMPLEMENTED: find_tool({tool_name})"

    @mcp.tool
    def show_tool_position(sector: str, x: int, y: int) -> str:
        """Shell tool placeholder for checking tool location by coordinates."""
        return f"NOT_IMPLEMENTED: show_tool_position({sector}, {x}, {y})"

    @mcp.tool
    def change_tool_status(tool_name: str, status: str, name_of_person: str) -> str:
        """Shell tool placeholder for updating tool status."""
        return (
            "NOT_IMPLEMENTED: "
            f"change_tool_status({tool_name}, {status}, {name_of_person})"
        )
