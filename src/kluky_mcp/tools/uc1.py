"""Tool access and position shells."""

from fastmcp import FastMCP

from kluky_mcp.db import get_db_connection
from kluky_mcp.models import (
    ChangeToolStatusInput,
    ListToolsInput,
    ShowToolPositionInput,
)

# citanie json file
import json
import os

# adresy pre kazde ESP na wifine
# v esp kode si zoberu staticke ip

import socket

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
    "LOST": "Stratené",
}

def check_led_status() -> bool:
    flag_path = os.path.join(os.path.dirname(__file__), "led_flag.json")
    try:
        with open(flag_path, "r") as f:
            #ak chyba value - blikame
            return json.load(f).get("leds_enabled", True)
        
    #zmizol file? blikame 
    except Exception:
        return True 


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
    name="get_led_flag",
    annotations={
        "title": "Get LED Flag",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    )
    def get_led_flag() -> str:
        """Returns whether LED positioning is currently enabled or disabled."""
        enabled = check_led_status()
        return "LED osvetlenie je zapnuté." if enabled else "LED osvetlenie je vypnuté."


    @mcp.tool(
        name="set_led_flag",
        annotations={
            "title": "Set LED Flag",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def set_led_flag(value: bool) -> str:
        """Enables or disables LED positioning."""
        flag_path = os.path.join(os.path.dirname(__file__), "led_flag.json")
        with open(flag_path, "w") as f:
            json.dump({"leds_enabled": value}, f)
        return "LED osvetlenie zapnuté." if value else "LED osvetlenie vypnuté."
    
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

        if not check_led_status():
            return "Ledky sú vypnuté."

        sector = params.sector.upper()
        pin = params.pin
        led = params.led
        # sector letter -> ESP32 ip
        ip = ESP32_MAP.get(sector)

        # zakladne checks
        if ip is None:
            return "Sector is not in the current ESP sector mapping."
        if led > 63:
            return "Led number does not exist on the current led strips"
        if sector not in ESP32_MAP:
            return "Sector does not exist in the current mapping"

        # return f"nieco sa dojebalo, kazdopadne, tu mas params: \n sector:{sector}, pin:{pin}, led:{led}, ip:{ip}"

        message = f"PIN:{pin},LED:{led}\n"

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(ESP32_TIMEOUT)
                s.connect((ip, ESP32_PORT))
                s.sendall(message.encode())
                response = s.recv(1024).decode().strip()
                return f"ESP32 {sector} ({ip}) odpoved: {response} braskiii les fucking gooooooooo"
        except TimeoutError:
            return f"DOJEBANEE1: ESP32 {sector} ({ip}) neodpovedalo do {ESP32_TIMEOUT}s"
        except ConnectionRefusedError:
            return f"DOJEBANEE2: ESP32 {sector} ({ip}) odmietlo connection."
        except OSError as e:
            return f"DOJEBANEE3: K ESP32 {sector} ({ip}) sa nepodarilo pripojit {e}"

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

                translated = translate_status(status)
                if status == "BORROWED" or status == "LOST" or status == "BROKEN":
                    return f"Náradie '{params.tool_name}' {translated} {params.name_of_person}."
                else:
                    return f"Náradie '{params.tool_name}' - stav: {translated}."

        finally:
            conn.close()
