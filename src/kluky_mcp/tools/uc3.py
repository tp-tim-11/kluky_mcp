"""Record-management tool shells."""

from fastmcp import FastMCP

from kluky_mcp.constants import TOOL_NAMESPACE
from kluky_mcp.formatters import format_not_implemented
from kluky_mcp.models import (
    AddRecordIfNotExistsInput,
    GetAllRecordsForNameInput,
    UpdateRecordInput,
)


def register(mcp: FastMCP) -> None:
    """Register UC3 record-management tools."""

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_add_record_if_not_exists",
        annotations={
            "title": "Add Record If Not Exists",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    def kluky_add_record_if_not_exists(params: AddRecordIfNotExistsInput) -> str:
        """Shell placeholder for adding a new record if missing."""
        return format_not_implemented("add_record_if_not_exists", params.model_dump())

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_get_all_records_for_name",
        annotations={
            "title": "Get All Records For Name",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kluky_get_all_records_for_name(
        params: GetAllRecordsForNameInput,
    ) -> list[dict[str, object]]:
        """Shell placeholder for listing records by person name."""
        _ = params
        return []

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_update_record",
        annotations={
            "title": "Update Record",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    def kluky_update_record(params: UpdateRecordInput) -> str:
        """Shell placeholder for updating an existing record."""
        return format_not_implemented("update_record", params.model_dump())
