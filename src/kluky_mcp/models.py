"""Pydantic input models for MCP tools."""

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional


class BaseInput(BaseModel):
    """Base model enforcing strict tool input validation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HealthCheckInput(BaseInput):
    """Input for deterministic connectivity health checks."""

    challenge: str = Field(
        default="kluky-health-check",
        description="Deterministic challenge value used to derive the health proof.",
        min_length=1,
        max_length=256,
    )


class ListToolsInput(BaseInput):
    """Input for listing available shop tools."""


class FindToolInput(BaseInput):
    """Input for finding a tool by name."""

    tool_name: str = Field(
        ...,
        description="The tool name to search for in inventory.",
        min_length=1,
        max_length=120,
    )


class ShowToolPositionInput(BaseInput):
    """Input for querying tool position by coordinates."""

    sector: str = Field(
        ...,
        description="Storage sector identifier.",
        min_length=1,
        max_length=32,
    )
    x: int = Field(..., description="Horizontal coordinate in the sector map.")
    y: int = Field(..., description="Vertical coordinate in the sector map.")

class ChangeToolStatusInput(BaseInput):
    """Input for changing tool status."""

    tool_name: str = Field(..., min_length=1, max_length=120)

    status: str = Field(
        ...,
        description="Target status value.",
        min_length=1,
        max_length=32,
    )

    name_of_person: Optional[str] = Field(
        None,
        description="Person who borrowed the tool (required only when status = borrowed).",
        max_length=120,
    )


class GetDocumentsInput(BaseInput):
    """Input for listing deterministic test documents."""


class GetDocumentInfoInput(BaseInput):
    """Input for retrieving document details by name or ID."""

    name: str | None = Field(
        default=None,
        description="Document name from the test catalog.",
        min_length=1,
        max_length=120,
    )
    document_id: int | None = Field(
        default=None,
        description="Document numeric identifier from the test catalog.",
        ge=1,
    )

    @model_validator(mode="after")
    def validate_identifier(self) -> "GetDocumentInfoInput":
        if self.name is None and self.document_id is None:
            raise ValueError("Provide either name or document_id.")
        return self


class AddRecordIfNotExistsInput(BaseInput):
    """Input for creating a new service record if it does not exist."""

    first_name: str = Field(..., description="Customer first name.", min_length=1)
    last_name: str = Field(..., description="Customer last name.", min_length=1)
    subject_name: str = Field(
        ...,
        description="Subject or item being serviced.",
        min_length=1,
    )
    what_i_am_fixing: str = Field(
        ...,
        description="What exact part is user fixing on item.",
        min_length=1,
    )
    raw_text: str = Field(
        ...,
        description="Original full text from the user, stored into raw_data.",
        min_length=1,
    )
    repaired_with: list[str] = Field(
        default_factory=list,
        description="Optional list of tools or materials used for repair.",
    )


class GetAllRecordsForNameInput(BaseInput):
    """Input for listing all records for a person."""

    first_name: str = Field(..., description="Customer first name.", min_length=1)
    last_name: str = Field(..., description="Customer last name.", min_length=1)


class UpdateRecordInput(BaseInput):
    """Input for updating an existing service record."""

    record_id: str = Field(
        ...,
        description="repair_records.id",
        min_length=1,
    )
    log_id: str = Field(
        ...,
        description="repair_logs.id",
        min_length=1,
    )
    what_i_am_fixing: str = Field(
        ...,
        description="What exact part is user fixing on item.",
        min_length=1,
    )
    raw_text: str = Field(
        ...,
        description="New original full text appended into raw_data.",
        min_length=1,
    )
    repaired_with: list[str] = Field(
        default_factory=list,
        description="Optional list of used tools or materials.",
    )
