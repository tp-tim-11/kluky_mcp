"""Record-management tool shells."""

from fastmcp import FastMCP

from kluky_mcp.constants import TOOL_NAMESPACE
from kluky_mcp.formatters import format_not_implemented
from kluky_mcp.models import (
    AddRecordIfNotExistsInput,
    GetAllRecordsForNameInput,
    UpdateRecordInput,
)
from kluky_mcp.pg_connection import get_db_connection


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
        """Add a new service record to the database."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO records (first_name, last_name, subject_name, what_i_am_fixing, repaired_with)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        params.first_name,
                        params.last_name,
                        params.subject_name,
                        params.what_i_am_fixing,
                        params.repaired_with,
                    ),
                )
                record_id = cur.fetchone()[0]
                conn.commit()
            return f"Record created successfully with ID: {record_id}"
        except Exception as e:
            conn.rollback()
            return f"Error creating record: {e}"
        finally:
            conn.close()

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
