"""Pydantic input models for MCP tools."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    tool_name: str = Field(..., description="Tool name.", min_length=1, max_length=120)
    status: str = Field(
        ...,
        description="Target status value, for example in_place or loaned.",
        min_length=1,
        max_length=32,
    )
    name_of_person: str = Field(
        ...,
        description="Person related to the status update.",
        min_length=1,
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
        description="Description of what is being fixed.",
        min_length=1,
    )
    repaired_with: list[str] = Field(
        ...,
        description="List of tools or materials used for repair.",
        min_length=1,
    )


class GetAllRecordsForNameInput(BaseInput):
    """Input for listing all records for a person."""

    first_name: str = Field(..., description="Customer first name.", min_length=1)
    last_name: str = Field(..., description="Customer last name.", min_length=1)


class UpdateRecordInput(BaseInput):
    """Input for updating an existing service record."""

    record_id: str = Field(
        ...,
        description="Record identifier in the service records list.",
        min_length=1,
    )
    what_i_am_fixing: str = Field(
        ...,
        description="Updated repair description.",
        min_length=1,
    )
    repaired_with: list[str] = Field(
        ...,
        description="Updated list of used tools or materials.",
        min_length=1,
    )
