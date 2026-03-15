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

class NewSessionInput(BaseInput):
    """Input for starting a new session."""
class LastUserMessageInput(BaseInput):
    """Input for retrieving the last user message."""
class SendTTSResponseInput(BaseInput):
    """Input for sending a text-to-speech response."""

    text: str = Field(
        ...,
        description="Text to be converted to speech and spoken.",
        min_length=1,
        max_length=400,
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
    pin: int = Field(..., description="Pin number the led strip is connected to.")
    led: int = Field(..., description="Led number of the located tool.")


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
    """Input for listing catalog candidates for documents."""

    queries: list[str] = Field(
        ...,
        description="One or more normalized user question variants.",
        min_length=1,
    )
    top_k: int = Field(
        default=8,
        description="Maximum number of catalog candidates to return.",
        ge=1,
        le=200,
    )
    manual_doc_id: str | None = Field(
        default=None,
        description="Optional parent manual doc_id filter.",
        min_length=1,
        max_length=255,
    )


class GetDocumentInfoInput(BaseInput):
    """Input for retrieving document details by doc_id and optional unit."""

    doc_id: str | None = Field(
        default=None,
        description="Document text identifier from stored index (doc_units.doc_id).",
        min_length=1,
        max_length=255,
    )
    manual_name: str | None = Field(
        default=None,
        description="Manual file name (e.g. manual_Bicykle_SK.pdf) used when doc_id is not known.",
        min_length=1,
        max_length=255,
    )
    unit_no: int | None = Field(
        default=None,
        description="Optional unit number filter to return a single section/unit.",
        ge=1,
    )

    @model_validator(mode="after")
    def _validate_identifier(self) -> "GetDocumentInfoInput":
        if not self.doc_id and not self.manual_name:
            raise ValueError("Either 'doc_id' or 'manual_name' must be provided.")
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
