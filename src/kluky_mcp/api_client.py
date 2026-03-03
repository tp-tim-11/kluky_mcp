"""API client skeleton to be implemented by the team."""

from typing import Any


async def make_api_request(
    endpoint: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    json_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stub API call function for future integration work."""
    _ = endpoint, method, params, json_data
    raise NotImplementedError(
        "NOT_IMPLEMENTED: make_api_request must be implemented by the team."
    )


def handle_api_error(exc: Exception) -> str:
    """Stub error-handler hook for future integration work."""
    _ = exc
    return "NOT_IMPLEMENTED: handle_api_error must be implemented by the team."
