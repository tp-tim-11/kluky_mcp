from fastmcp import FastMCP

TEST_CATALOG_LABEL = "TEST_PURPOSE_DOCUMENT_CATALOG"
TEST_DOCUMENT_CATALOG: list[dict[str, str | int]] = [
    {
        "id": 1,
        "name": "TEST_DOC_STARTUP_CHECKLIST",
        "summary": "Test-only startup checklist for MCP integration validation.",
    },
    {
        "id": 2,
        "name": "TEST_DOC_TOOL_CONTRACTS",
        "summary": "Test-only tool input-output contract reference for teammates.",
    },
    {
        "id": 3,
        "name": "TEST_DOC_DEPLOYMENT_NOTES",
        "summary": "Test-only deployment notes used for deterministic MCP checks.",
    },
]


def register(mcp: FastMCP) -> None:
    @mcp.tool
    def get_documents() -> dict[str, str | list[dict[str, str | int]]]:
        """Return the static document catalog marked explicitly for tests."""
        return {
            "catalog_label": TEST_CATALOG_LABEL,
            "documents": TEST_DOCUMENT_CATALOG,
        }

    @mcp.tool
    def get_document_info(
        name: str | None = None,
        document_id: int | None = None,
    ) -> str:
        """Get deterministic test-document details by name or ID."""
        if document_id is None and name is None:
            return "Provide either name or document_id."

        for document in TEST_DOCUMENT_CATALOG:
            if document_id is not None and document["id"] == document_id:
                return (
                    f"[{TEST_CATALOG_LABEL}] "
                    f"id={document['id']} name={document['name']} "
                    f"summary={document['summary']}"
                )

            if (
                name is not None
                and str(document["name"]).lower() == name.strip().lower()
            ):
                return (
                    f"[{TEST_CATALOG_LABEL}] "
                    f"id={document['id']} name={document['name']} "
                    f"summary={document['summary']}"
                )

        return "Document not found in test catalog."
