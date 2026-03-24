"""Server tests for MCP server composition."""

from typing import Any

import pytest

from kluky_mcp import server


class _ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(
        self,
        name: str,
        annotations: dict[str, object] | None = None,
    ) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[name] = func
            return func

        return decorator


def test_server_imports() -> None:
    """Verify server module imports cleanly."""
    assert hasattr(server, "create_server")
    assert hasattr(server, "main")
    assert hasattr(server, "mcp")


def test_server_registers_expected_tools() -> None:
    """Verify the complete expected tool set is registered."""
    registry = _ToolRegistry()

    server.register_health(registry)  # type: ignore[arg-type]
    server.register_uc0(registry)  # type: ignore[arg-type]
    server.register_uc1(registry)  # type: ignore[arg-type]
    server.register_uc2(registry)  # type: ignore[arg-type]
    server.register_uc3(registry)  # type: ignore[arg-type]

    expected_tools = {
        "health_check",
        "new_session",
        "last_user_message",
        "send_tts_response",
        "list_tools",
        "show_tool_position",
        "change_tool_status",
        "get_documents",
        "get_document_info",
        "add_record_if_not_exists",
        "get_all_records_for_name",
        "update_record",
        "export_all_records_to_csv_desktop",
    }

    assert expected_tools == set(registry.tools.keys())
