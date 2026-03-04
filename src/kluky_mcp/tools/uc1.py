"""Tool access and position shells."""

from fastmcp import FastMCP

from kluky_mcp.constants import TOOL_NAMESPACE
from kluky_mcp.db import get_db_connection
from kluky_mcp.formatters import format_not_implemented
from kluky_mcp.models import (
    ChangeToolStatusInput,
    FindToolInput,
    ListToolsInput,
    ShowToolPositionInput,
)

# adresy pre kazde ESP na wifine 
# v esp kode si zoberu staticke ip

# import socket
ESP32_MAP: dict[str, str] = {
    "A": "192.168.43.101",
    "B": "192.168.43.102",
    "C": "192.168.43.103",
    "D": "192.168.43.104",
}

# server <-> esp = tcp comm
ESP32_PORT = 8080
ESP32_TIMEOUT = 5

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
        """List all available tools from inventory."""
        _ = params
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT nazov FROM resources WHERE deleted = false ORDER BY nazov"
                )
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

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
        """Find a tool by name in the inventory."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, nazov, pozicia, status, vypozicane_komu FROM resources WHERE nazov ILIKE %s AND deleted = false",
                    (f"%{params.tool_name}%",),
                )
                row = cur.fetchone()
                if row is None:
                    return f"Tool '{params.tool_name}' not found."
                return (
                    f"ID: {row[0]}\n"
                    f"Name: {row[1]}\n"
                    f"Position: {row[2]}\n"
                    f"Status: {row[3]}\n"
                    f"Borrowed to: {row[4] or 'N/A'}"
                )
        finally:
            conn.close()

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
        """Blinks the LED above the tool on the correct ESP32 strip."""

        sector = params.sector.upper()
        pin = params.x
        led = params.y
        # sector letter -> ESP32 ip
        ip = ESP32_MAP.get(sector)

        # zakladne checks
        if ip is None:
            return f"Sector is not in the current ESP sector mapping."
        if led>63:
            return f"Led number does not exist on the current led strips"
        if sector not in ESP32_MAP:
            return f"Sector does not exist in the current "
        
        return f"nieco sa dojebalo, kazdopadne, tu mas params: \n sector:{sector}, pin:{pin}, led:{led}, ip:{ip}"
        
        message = f"PIN:{pin},LED:{led}\n"

        # pripojenie na esp neni mozne lebo neni esp, tak zatial zakomentovane
        # vraciam iba dojebalo sa

        # try:
        #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        #         s.settimeout(ESP32_TIMEOUT)
        #         s.connect((ip, ESP32_PORT))
        #         s.sendall(message.encode())
        #         response = s.recv(1024).decode().strip()
        #         return f"ESP32 {sector} ({ip}) responded: {response}"
        # except TimeoutError:
        #     return f"FAILURE: ESP32 {sector} ({ip}) did not respond within {ESP32_TIMEOUT}s"
        # except ConnectionRefusedError:
        #     return f"FAILURE: ESP32 {sector} ({ip}) refused connection."
        # except OSError as e:
        #     return f"FAILURE: could not reach ESP32 {sector} ({ip}) — {e}"

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
