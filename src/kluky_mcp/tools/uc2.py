"""Document-related shell tools."""

from fastmcp import FastMCP

from kluky_mcp.constants import NOT_IMPLEMENTED_PREFIX, TOOL_NAMESPACE
from kluky_mcp.formatters import format_not_implemented
from kluky_mcp.models import GetDocumentInfoInput, GetDocumentsInput


def register(mcp: FastMCP) -> None:
    """Register UC2 document tools."""

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_get_documents",
        annotations={
            "title": "Get Documents",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kluky_get_documents(params: GetDocumentsInput) -> dict[str, str]:
        """Shell placeholder for listing documents."""
        _ = params
        return {
            "status": NOT_IMPLEMENTED_PREFIX,
            "tool": "kluky_get_documents",
        }

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_get_document_info",
        annotations={
            "title": "Get Document Info",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kluky_get_document_info(params: GetDocumentInfoInput) -> str:
        """Shell placeholder for getting document details by name or ID."""
        return format_not_implemented("get_document_info", params.model_dump())
