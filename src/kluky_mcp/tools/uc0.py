import requests
from fastmcp import FastMCP

from kluky_mcp.models import NewSessionInput, SendTTSResponseInput


def register(mcp: FastMCP) -> None:
    """Register UC0 tools."""

    @mcp.tool(name="new_session")
    def new_session(params: NewSessionInput) -> str:
        """Clear the current conversation and start a new session."""

        response: requests.Response = requests.get(url="http://localhost:8321/v1/new_session")

        if response.status_code == 200:
            return response.text
        else:
            print(f"Request failed: {response.status_code} {response.text}")
            return f"Request failed: {response.status_code} {response.text}"

    @mcp.tool(name="send_tts_response")
    def send_tts_response(params: SendTTSResponseInput) -> str:
        """Send a text-to-speech response."""

        response: requests.Response = requests.post(url="http://localhost:8321/v1/speak", json={"text": params.text})

        if response.status_code == 200:
            return response.text
        else:
            return f"Request failed: {response.status_code} {response.text}"
