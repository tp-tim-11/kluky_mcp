"""Health-check tests for the health tool."""

from typing import Any

import pytest

from kluky_mcp.models import HealthCheckInput
from kluky_mcp.tools.health import register as register_health


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


@pytest.fixture()
def health_tools() -> dict[str, Any]:
    registry = _ToolRegistry()
    register_health(registry)  # type: ignore[arg-type]
    return registry.tools


def test_health_check_returns_placeholder_status(health_tools: dict[str, Any]) -> None:
    """Health check should return NOT_IMPLEMENTED placeholder status."""
    result = health_tools["health_check"](HealthCheckInput(challenge="test-challenge"))

    assert result["status"] == "NOT_IMPLEMENTED"


def test_health_check_response_shape(health_tools: dict[str, Any]) -> None:
    """Response should include status, tool, and challenge."""
    challenge = "abc123"
    result = health_tools["health_check"](HealthCheckInput(challenge=challenge))

    assert "status" in result
    assert result["tool"] == "health_check"
    assert result["challenge"] == challenge
