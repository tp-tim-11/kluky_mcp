"""UC0 tests for session, message, and TTS tools."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest

from kluky_mcp.models import LastUserMessageInput, NewSessionInput, SendTTSResponseInput
from kluky_mcp.tools.uc0 import register as register_uc0


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
def uc0_tools() -> dict[str, Any]:
    registry = _ToolRegistry()
    register_uc0(registry)  # type: ignore[arg-type]
    return registry.tools


class TestNewSession:
    def test_new_session_returns_response_on_success(
        self,
        uc0_tools: dict[str, Any],
    ) -> None:
        with patch("kluky_mcp.tools.uc0.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "session_cleared"
            mock_get.return_value = mock_response

            result = uc0_tools["new_session"](NewSessionInput())

            assert result == "session_cleared"
            mock_get.assert_called_once_with(url="http://localhost:8321/v1/new_session")

    def test_new_session_returns_error_on_failure(
        self,
        uc0_tools: dict[str, Any],
    ) -> None:
        with patch("kluky_mcp.tools.uc0.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_get.return_value = mock_response

            result = uc0_tools["new_session"](NewSessionInput())

            assert result == "Request failed: 500 Internal Server Error"


class TestLastUserMessage:
    def test_last_user_message_returns_message_on_success(
        self,
        uc0_tools: dict[str, Any],
    ) -> None:
        with patch("kluky_mcp.tools.uc0.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "Ahoj, potrebujem opravit bicykel"
            mock_get.return_value = mock_response

            result = uc0_tools["last_user_message"](LastUserMessageInput())

            assert result == "Ahoj, potrebujem opravit bicykel"
            mock_get.assert_called_once_with(
                url="http://localhost:8321/v1/last_user_message"
            )

    def test_last_user_message_returns_error_on_failure(
        self,
        uc0_tools: dict[str, Any],
    ) -> None:
        with patch("kluky_mcp.tools.uc0.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_get.return_value = mock_response

            result = uc0_tools["last_user_message"](LastUserMessageInput())

            assert result == "Request failed: 404 Not Found"


class TestSendTTSResponse:
    def test_send_tts_response_returns_response_on_success(
        self,
        uc0_tools: dict[str, Any],
    ) -> None:
        with patch("kluky_mcp.tools.uc0.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "spoken"
            mock_post.return_value = mock_response

            result = uc0_tools["send_tts_response"](
                SendTTSResponseInput(text="Dobrý deň, ako vam možem pomôct?")
            )

            assert result == "spoken"
            mock_post.assert_called_once_with(
                url="http://localhost:8321/v1/speak",
                json={"text": "Dobrý deň, ako vam možem pomôct?"},
            )

    def test_send_tts_response_returns_error_on_failure(
        self,
        uc0_tools: dict[str, Any],
    ) -> None:
        with patch("kluky_mcp.tools.uc0.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.text = "Service Unavailable"
            mock_post.return_value = mock_response

            result = uc0_tools["send_tts_response"](SendTTSResponseInput(text="Test"))

            assert result == "Request failed: 503 Service Unavailable"
