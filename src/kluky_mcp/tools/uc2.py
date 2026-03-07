"""Document-related shell tools."""

import re
from typing import Any

from fastmcp import FastMCP

from kluky_mcp.constants import TOOL_NAMESPACE
from kluky_mcp.db import get_db_connection
from kluky_mcp.models import GetDocumentInfoInput, GetDocumentsInput
from kluky_mcp.tools.uc02_utils.pageIndexRetrieval import (
    fetch_document_text,
    fetch_document_units_catalog,
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
    units_catalog: list[dict[str, Any]],
    *,
    queries: list[str],
    manual_doc_id: str | None,
    top_k: int,
) -> list[dict[str, Any]]:
    def normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower())

    query_terms = {
        term
        for query in queries
        for term in re.findall(r"\w+", normalize(query))
        if len(term) >= 3
    }

    scored_candidates: list[tuple[int, dict[str, Any]]] = []

    for item in units_catalog:
        if not isinstance(item, dict):
            continue

        doc_id = item.get("doc_id")
        if not isinstance(doc_id, str):
            continue

        if manual_doc_id and not (
            doc_id == manual_doc_id or doc_id.startswith(f"{manual_doc_id}::")
        ):
            continue

        manual_name = str(item.get("manual_name") or item.get("document_name") or "")
        title = str(item.get("title") or "")
        summary = str(item.get("summary") or "")
        haystack = normalize(f"{manual_name} {title} {summary}")

        score = 0
        for term in query_terms:
            if term in haystack:
                score += 1
            if term and term in normalize(title):
                score += 2

        scored_candidates.append(
            (
                score,
                {
                    "manual": manual_name,
                    "title": title or None,
                    "unit_no": item.get("unit_no"),
                    "start_page": item.get("start_page"),
                    "end_page": item.get("end_page"),
                    "summary": item.get("summary"),
                    "updated_at": item.get("updated_at"),
                    "selection_mode": "catalog_only",
                },
            )
        )

    if not scored_candidates:
        # fallback: return newest catalog rows even when query terms do not match
        for item in units_catalog[:top_k]:
            scored_candidates.append(
                (
                    0,
                    {
                        "manual": item.get("manual_name") or item.get("document_name"),
                        "title": item.get("title"),
                        "unit_no": item.get("unit_no"),
                        "start_page": item.get("start_page"),
                        "end_page": item.get("end_page"),
                        "summary": item.get("summary"),
                        "updated_at": item.get("updated_at"),
                        "selection_mode": "catalog_only",
                    },
                )
            )

    scored_candidates.sort(
        key=lambda x: (
            x[0],
            str(x[1].get("updated_at") or ""),
            str(x[1].get("manual") or ""),
            int(x[1].get("unit_no") or 2147483647),
        ),
        reverse=True,
    )

    return [candidate for _, candidate in scored_candidates[:top_k]]


def _topics_by_manual(
    units_catalog: list[dict[str, Any]],
    *,
    manual_doc_id: str | None,
    max_manuals: int = 10,
    max_sections_per_manual: int = 30,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = {}

    for item in units_catalog:
        if not isinstance(item, dict):
            continue

        doc_id = item.get("doc_id")
        if not isinstance(doc_id, str):
            continue

        if manual_doc_id and not (
            doc_id == manual_doc_id or doc_id.startswith(f"{manual_doc_id}::")
        ):
            continue

        manual_name = str(
            item.get("manual_name") or item.get("document_name") or "Neznamy manual"
        ).strip()
        if manual_name not in grouped and len(grouped) >= max_manuals:
            continue

        title = str(item.get("title") or "").strip()
        if not title:
            continue

        sections = grouped.setdefault(manual_name, [])
        if title not in sections and len(sections) < max_sections_per_manual:
            sections.append(title)

    return [
        {
            "manual": manual,
            "topics": topics,
        }
        for manual, topics in grouped.items()
    ]


def _manuals_catalog(units_catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, int] = {}
    for item in units_catalog:
        if not isinstance(item, dict):
            continue
        manual_name = str(
            item.get("manual_name") or item.get("document_name") or "Neznamy manual"
        ).strip()
        if not manual_name:
            manual_name = "Neznamy manual"
        grouped[manual_name] = grouped.get(manual_name, 0) + 1

    return [
        {"manual": manual_name, "sections_count": sections_count}
        for manual_name, sections_count in sorted(grouped.items(), key=lambda x: x[0])
    ]


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
        """Return document catalog candidates for agent-side selection."""
        queries = _normalize_queries(params.queries)

        conn = get_db_connection()
        try:
            units_catalog = fetch_document_units_catalog(conn)

        finally:
            conn.close()

        candidates = _catalog_candidates(
            units_catalog,
            queries=queries,
            manual_doc_id=params.manual_doc_id,
            top_k=params.top_k,
        )
        return {
            "queries": queries,
            "top_k": params.top_k,
            "manual_doc_id_filter": params.manual_doc_id,
            "count": len(candidates),
            "manuals_catalog": _manuals_catalog(units_catalog),
            "topics_by_manual": _topics_by_manual(
                units_catalog,
                manual_doc_id=params.manual_doc_id,
            ),
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
                manual_name=params.manual_name,
                unit_no=params.unit_no,
            )
        finally:
            conn.close()
