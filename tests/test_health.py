"""Health-check test skeletons for team implementation."""

import pytest


@pytest.mark.skip(reason="TODO(team): implement placeholder response checks")
def test_health_check_returns_placeholder_status() -> None:
    """Health check should return NOT_IMPLEMENTED placeholder status."""


@pytest.mark.skip(reason="TODO(team): implement response-shape assertions")
def test_health_check_response_shape() -> None:
    """Response should include status, tool, and challenge."""
