"""Tool access and position shells."""

from fastmcp import FastMCP

from kluky_mcp.db import get_db_connection
from kluky_mcp.models import (
    ChangeToolStatusInput,
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

STATUS_TRANSLATION = {
    "AVAILABLE": "Na mieste",
    "BORROWED": "Požičané",
    "BROKEN": "Pokazené",
}


def translate_status(status: str | None) -> str:
    """Translate status to Slovak for user-facing output."""
    if status is None:
        return "-"
    normalized = status.strip().upper()
    return STATUS_TRANSLATION.get(normalized, status)


def register(mcp: FastMCP) -> None:
    """Register UC1 tools."""

    @mcp.tool(
        name="list_tools",
        annotations={
            "title": "List Tools",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def list_tools(params: ListToolsInput) -> list[str]:
        """List all available tools from inventory with id, name, status and position."""
        _ = params
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, esp, pin, led,  status, borrowed_by
                    FROM resources
                    WHERE deleted = false
                    ORDER BY id
                    """
                )

                rows = cur.fetchall()

                if not rows:
                    return ["No tools found."]

                return [
                    f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} {translate_status(r[5])} | Vypožičal: {r[6] or '-'}"
                    for r in rows
                ]

        finally:
            conn.close()

    @mcp.tool(
        name="show_tool_position",
        annotations={
            "title": "Show Tool Position",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def show_tool_position(params: ShowToolPositionInput) -> str:
        """Blinks the LED above the tool on the correct ESP32 strip."""

        sector = params.sector.upper()
        pin = params.x
        led = params.y
        # sector letter -> ESP32 ip
        ip = ESP32_MAP.get(sector)

        # zakladne checks
        if ip is None:
            return "Sector is not in the current ESP sector mapping."
        if led > 63:
            return "Led number does not exist on the current led strips"
        if sector not in ESP32_MAP:
            return "Sector does not exist in the current "

        return f"nieco sa dojebalo, kazdopadne, tu mas params: \n sector:{sector}, pin:{pin}, led:{led}, ip:{ip}"

        message = f"PIN:{pin},LED:{led}\n"  # noqa: F841

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
        name="change_tool_status",
        annotations={
            "title": "Change Tool Status",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    def change_tool_status(params: ChangeToolStatusInput) -> str:
        """Update tool status and optionally who borrowed it."""
        conn = get_db_connection()
        status = params.status.strip().upper()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE resources
                    SET
                        status = %s,
                        borrowed_by = CASE
                            WHEN %s = 'BORROWED' THEN %s
                            ELSE NULL
                        END
                    WHERE deleted = false
                      AND (
                        id::text = %s
                        OR name = %s
                      )
                    """,
                    (
                        status,
                        status,
                        params.name_of_person,
                        params.tool_name,
                        params.tool_name,
                    ),
                )

                if cur.rowcount == 0:
                    return f"Tool '{params.tool_name}' not found."

                conn.commit()

                if status == "BORROWED":
                    return f"Náradie '{params.tool_name}' požičané {params.name_of_person}."
                else:
                    translated = translate_status(status)
                    return f"Náradie '{params.tool_name}' - stav: {translated}."

        finally:
            conn.close()
