"""Document-related shell tools."""

from typing import Any

from fastmcp import FastMCP

from kluky_mcp.constants import TOOL_NAMESPACE
from kluky_mcp.db import get_db_connection
from kluky_mcp.models import GetDocumentInfoInput, GetDocumentsInput, GetGuideInput
from kluky_mcp.tools.uc02_utils.pageIndexRetrieval import (
    fetch_document_library,
    fetch_document_text,
)


def _normalize_queries(queries: list[str]) -> list[str]:
    normalized: list[str] = []
    for query in queries:
        value = query.strip()
        if not value or value in normalized:
            continue
        normalized.append(value)
    if not normalized:
        raise RuntimeError(
            "Parameter 'queries' must contain at least one non-empty query."
        )
    return normalized


def _catalog_candidates(
    library: dict[str, Any],
    *,
    manual_doc_id: str | None,
    top_k: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    for item in library.get("documents", []):
        if not isinstance(item, dict):
            continue

        doc_id = item.get("doc_id")
        if not isinstance(doc_id, str):
            continue

        if manual_doc_id and not (
            doc_id == manual_doc_id or doc_id.startswith(f"{manual_doc_id}::")
        ):
            continue

        candidates.append(
            {
                "doc_id": doc_id,
                "document_name": item.get("document_name"),
                "summary": item.get("summary"),
                "source_path": item.get("source_path"),
                "source_type": item.get("source_type"),
                "unit_count": item.get("unit_count"),
                "updated_at": item.get("updated_at"),
                "selection_mode": "catalog_only",
            }
        )

    return candidates[:top_k]


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
    def kluky_get_documents(params: GetDocumentsInput) -> dict[str, Any]:
        """Shell placeholder for listing documents."""
        _ = params
        conn = get_db_connection()
        try:
            return fetch_document_library(conn)

        finally:
            conn.close()

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_get_guide",
        annotations={
            "title": "Get Guide",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kluky_get_guide(params: GetGuideInput) -> dict[str, Any]:
        """Return document catalog candidates for agent-side selection."""
        queries = _normalize_queries(params.queries)

        conn = get_db_connection()
        try:
            library = fetch_document_library(conn)
        finally:
            conn.close()

        candidates = _catalog_candidates(
            library,
            manual_doc_id=params.manual_doc_id,
            top_k=params.top_k,
        )
        return {
            "queries": queries,
            "top_k": params.top_k,
            "manual_doc_id_filter": params.manual_doc_id,
            "count": len(candidates),
            "results": candidates,
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
    def kluky_get_document_info(params: GetDocumentInfoInput) -> dict[str, Any]:
        """Get document details by doc_id and optional unit_no."""
        conn = get_db_connection()
        try:
            return fetch_document_text(
                conn,
                doc_id=params.doc_id,
                unit_no=params.unit_no,
            )
        finally:
            conn.close()
