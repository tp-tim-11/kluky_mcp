"""Formatting helpers for shell tool responses."""

import json
from collections.abc import Mapping
from typing import Any

from kluky_mcp.constants import CHARACTER_LIMIT, NOT_IMPLEMENTED_PREFIX


def truncate_text(text: str, max_length: int = CHARACTER_LIMIT) -> str:
    """Truncate long text responses to keep context usage predictable."""
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}\n\n[Truncated at {max_length} characters.]"


def format_not_implemented(tool_name: str, payload: Mapping[str, Any]) -> str:
    """Create deterministic placeholders for unimplemented tools."""
    serialized_payload = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return truncate_text(
        f"{NOT_IMPLEMENTED_PREFIX}: {tool_name} payload={serialized_payload}"
    )
