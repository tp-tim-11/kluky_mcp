import hashlib
import socket
import sys

from fastmcp import FastMCP

_SERVER_FINGERPRINT = hashlib.sha256(
    f"{socket.gethostname()}|{sys.executable}|kluky-mcp-health-v1".encode()
).hexdigest()


def register(mcp: FastMCP) -> None:
    @mcp.tool
    def health_check(challenge: str = "kluky-health-check") -> dict[str, str]:
        """Return a deterministic host-bound proof for connectivity testing."""
        proof = hashlib.sha256(
            f"{challenge}|{_SERVER_FINGERPRINT}|kluky-mcp-proof-v1".encode()
        ).hexdigest()

        return {
            "status": "ok",
            "challenge": challenge,
            "fingerprint": _SERVER_FINGERPRINT,
            "proof": proof,
            "algorithm": "sha256",
        }
