from __future__ import annotations

import re
import tempfile
import time
from pathlib import Path
from typing import Any

from pageindex import PageIndexClient

from kluky_mcp.db import get_db_connection
from kluky_mcp.settings import settings

from .pageIndexUtils import (
    DocUnit,
    PageIndexStore,
    convert_to_markdown,
    stable_doc_id_from_doc_key,
    stable_doc_id_from_source_path,
)


def _run_pageindex(input_path: str) -> dict[str, Any]:
    src = Path(input_path)
    if not src.exists():
        raise RuntimeError(f"Input file does not exist: {input_path}")

    api_key = settings.pageindex_api_key.strip()
    if not api_key:
        raise RuntimeError(
            "Missing PageIndex API key. Set PAGEINDEX_API_KEY "
            "(or FIT_PAGEINDEX_API_KEY) in .env/settings."
        )

    client = PageIndexClient(api_key=api_key)

    def extract_doc_id(response: dict[str, Any]) -> str:
        candidates = [
            response.get("doc_id"),
            (response.get("data") or {}).get("doc_id")
            if isinstance(response.get("data"), dict)
            else None,
            (response.get("document") or {}).get("doc_id")
            if isinstance(response.get("document"), dict)
            else None,
        ]
        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise RuntimeError(f"Unable to extract doc_id from submit response: {response}")

    def extract_tree(response: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(response, dict):
            raise RuntimeError("PageIndex get_tree() returned non-dict response.")

        if isinstance(response.get("structure"), list):
            return response

        data = response.get("data")
        if isinstance(data, dict):
            if isinstance(data.get("structure"), list):
                return data
            if isinstance(data.get("tree"), dict):
                return data["tree"]

        tree = response.get("tree")
        if isinstance(tree, dict):
            return tree

        result = response.get("result")
        if isinstance(result, list):
            return {
                "doc_name": response.get("doc_id"),
                "structure": [node for node in result if isinstance(node, dict)],
            }

        raise RuntimeError(
            f"Unable to extract tree payload from get_tree response: {response}"
        )

    def submit_and_get_tree(file_path: str) -> dict[str, Any]:
        submit_response = client.submit_document(file_path=file_path)
        remote_doc_id = extract_doc_id(submit_response)

        last_error: Exception | None = None
        for _attempt in range(20):
            try:
                tree_response = client.get_tree(doc_id=remote_doc_id, node_summary=True)
                tree_payload = extract_tree(tree_response)
                tree_payload.setdefault("pageindex_doc_id", remote_doc_id)
                return tree_payload
            except Exception as exc:
                last_error = exc
                time.sleep(1.5)

        raise RuntimeError(
            f"PageIndex tree was not ready for doc_id '{remote_doc_id}'."
        ) from last_error

    ext = src.suffix.lower()
    if ext == ".pdf":
        return submit_and_get_tree(str(src.resolve()))

    md_path = src
    temp_md_path: Path | None = None
    if ext not in {".md", ".markdown"}:
        md_text = convert_to_markdown(str(src.resolve()))
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(md_text)
            tmp.flush()
        temp_md_path = Path(tmp.name)
        md_path = temp_md_path

    try:
        return submit_and_get_tree(str(md_path))
    finally:
        if temp_md_path is not None and temp_md_path.exists():
            temp_md_path.unlink()


def _node_text_payload(node: dict[str, Any]) -> str:
    def _norm(s: str) -> str:
        return re.sub(r"\W+", "", s, flags=re.UNICODE).lower()

    title = str(node.get("title") or "").strip()
    text_value = str(node.get("text") or "").strip()

    if text_value:
        lines = text_value.splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines and title:
            first_line_clean = re.sub(r"^\s*#+\s*", "", lines[0]).strip()
            if _norm(first_line_clean) == _norm(title):
                lines = lines[1:]
                while lines and not lines[0].strip():
                    lines.pop(0)
        text_value = "\n".join(lines).strip()

    if not text_value and node.get("summary"):
        # Fallback when provider returns summary-only nodes.
        text_value = str(node["summary"]).strip()

    parts: list[str] = []
    if text_value:
        parts.append(text_value)

    start_index = node.get("start_index")
    end_index = node.get("end_index")
    if start_index is not None or end_index is not None:
        parts.append(f"[PageRange: {start_index}..{end_index}]")

    return "\n".join(parts).strip()


def _short_summary(text: str, *, max_len: int = 240) -> str:
    clean = " ".join(text.split()).strip()
    if not clean:
        return ""
    if len(clean) <= max_len:
        return clean
    return f"{clean[: max_len - 1].rstrip()}..."


def _node_summary(node: dict[str, Any], payload_text: str) -> str:
    raw_summary = node.get("summary")
    if isinstance(raw_summary, str) and raw_summary.strip():
        return _short_summary(raw_summary)
    return _short_summary(payload_text)


def _flatten_tree_to_units(
    tree: dict[str, Any], *, min_text_len: int = 20
) -> list[DocUnit]:
    units: list[DocUnit] = []

    def visit(node: dict[str, Any], path: list[str]) -> None:
        title = str(node.get("title") or "")
        next_path = [*path]
        if title:
            next_path.append(title)

        payload = _node_text_payload(node)
        if len(payload.strip()) >= min_text_len:
            heading_path = " > ".join(next_path) if next_path else None
            units.append(
                DocUnit(
                    unit_type="section",
                    unit_no=len(units) + 1,
                    title=title or (path[-1] if path else None),
                    heading_path=heading_path,
                    summary=_node_summary(node, payload),
                    text=payload,
                )
            )

        children = node.get("nodes") or []
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    visit(child, next_path)

    if not isinstance(tree, dict):
        raise RuntimeError("Unexpected PageIndex JSON format: expected root object.")

    if isinstance(tree.get("structure"), list):
        for root_node in tree.get("structure", []):
            if isinstance(root_node, dict):
                visit(root_node, [])
    else:
        visit(tree, [])

    return units


def _tree_preview(tree: dict[str, Any]) -> dict[str, Any]:
    if isinstance(tree.get("structure"), list):
        roots = [n for n in tree.get("structure", []) if isinstance(n, dict)]
        first = roots[0] if roots else {}
        return {
            "doc_name": tree.get("doc_name"),
            "root_count": len(roots),
            "first_root_title": first.get("title") if isinstance(first, dict) else None,
            "first_root_node_id": first.get("node_id")
            if isinstance(first, dict)
            else None,
            "first_root_children_count": len(first.get("nodes") or [])
            if isinstance(first, dict)
            else 0,
        }

    return {
        "title": tree.get("title"),
        "node_id": tree.get("node_id"),
        "children_count": len(tree.get("nodes") or []),
    }


def _extract_top_level_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(tree.get("structure"), list):
        roots = [n for n in tree.get("structure", []) if isinstance(n, dict)]
        if len(roots) == 1 and isinstance(roots[0].get("nodes"), list):
            return [n for n in roots[0].get("nodes", []) if isinstance(n, dict)]
        return roots

    nodes = tree.get("nodes") if isinstance(tree, dict) else None
    if isinstance(nodes, list) and nodes:
        return [n for n in nodes if isinstance(n, dict)]
    return [tree] if isinstance(tree, dict) else []


def _is_probable_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if len(s) < 4 or len(s) > 120:
        return False
    if s.endswith("."):
        return False
    if re.match(r"^\d+[\.)]\s+\S+", s):
        return True

    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return upper_ratio >= 0.75


def _split_sections_from_text(
    text: str, *, min_section_chars: int = 180
) -> list[dict[str, Any]]:
    lines = [ln.strip() for ln in text.splitlines()]
    sections: list[dict[str, Any]] = []

    current_title = "ÚVOD"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        body = "\n".join(ln for ln in current_lines if ln).strip()
        if len(body) >= min_section_chars:
            sections.append(
                {
                    "title": current_title,
                    "summary": _short_summary(body),
                    "text": body,
                }
            )
        current_lines = []

    for line in lines:
        if _is_probable_heading(line):
            flush()
            current_title = line
            continue
        current_lines.append(line)

    flush()
    return sections


def _derive_top_level_nodes(tree: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = _extract_top_level_nodes(tree)
    if len(nodes) > 1:
        return nodes

    only_node = nodes[0] if nodes else tree
    if isinstance(only_node, dict):
        raw_text = only_node.get("text")
        if isinstance(raw_text, str) and raw_text.strip():
            sections = _split_sections_from_text(raw_text)
            if len(sections) >= 3:
                return sections

    return nodes


def ingest_with_pageindex(
    input_path: str,
    *,
    doc_key: str | None = None,
    include_tree_json: bool = False,
    preview_units_limit: int = 3,
    split_top_level_docs: bool = True,
    manual_code: str = "1",
) -> dict[str, Any]:
    tree = _run_pageindex(input_path)

    source_type = Path(input_path).suffix.lower().lstrip(".") or "unknown"

    conn = get_db_connection()
    store = PageIndexStore(conn)
    docs_written: list[dict[str, Any]] = []
    units_preview: list[dict[str, Any]] = []

    try:
        if split_top_level_docs:
            top_nodes = _derive_top_level_nodes(tree)
            if not top_nodes:
                raise RuntimeError("PageIndex returned no top-level nodes to split.")

            if doc_key:
                base_doc_id = stable_doc_id_from_doc_key(doc_key)
            else:
                base_doc_id = stable_doc_id_from_source_path(input_path)

            manual_units: list[DocUnit] = []
            for i, node in enumerate(top_nodes, start=1):
                section_code = f"{manual_code}.{i}"
                section_title = str(node.get("title") or f"Section {section_code}")
                payload_text = _node_text_payload(node)
                if payload_text:
                    manual_units.append(
                        DocUnit(
                            unit_type="section",
                            unit_no=i,
                            title=f"{section_code} {section_title}",
                            heading_path=f"Manual {manual_code}",
                            summary=_node_summary(node, payload_text),
                            text=payload_text,
                        )
                    )

                child_doc_id = f"{base_doc_id}::{section_code}"
                child_units = _flatten_tree_to_units(node)
                if not child_units:
                    continue
                store.reindex_doc(
                    doc_id=child_doc_id,
                    source_path=input_path,
                    source_type=source_type,
                    units=child_units,
                )
                docs_written.append(
                    {
                        "doc_id": child_doc_id,
                        "section_code": section_code,
                        "section_title": section_title,
                        "unit_count": len(child_units),
                    }
                )

            if not docs_written:
                raise RuntimeError("Split mode produced no child documents.")

            store.reindex_doc(
                doc_id=base_doc_id,
                source_path=input_path,
                source_type=source_type,
                units=manual_units
                or [
                    DocUnit(
                        unit_type="section",
                        unit_no=1,
                        title=f"Manual {manual_code}",
                        heading_path=f"Manual {manual_code}",
                        summary="Manual index generated from top-level sections.",
                        text="Manual index generated from top-level sections.",
                    )
                ],
            )
            docs_written.insert(
                0,
                {
                    "doc_id": base_doc_id,
                    "section_code": str(manual_code),
                    "section_title": f"Manual {manual_code}",
                    "unit_count": len(manual_units) if manual_units else 1,
                    "is_parent": True,
                },
            )

            first_child = docs_written[1] if len(docs_written) > 1 else docs_written[0]
            units_preview = [
                {
                    "unit_type": "section",
                    "unit_no": None,
                    "title": first_child.get("section_title"),
                    "heading_path": f"Manual {manual_code}",
                    "summary": first_child.get("section_title"),
                    "text_preview": f"Stored as document id {first_child.get('doc_id')}",
                }
            ]
            doc_id = base_doc_id
            unit_count = sum(int(d["unit_count"]) for d in docs_written)
        else:
            units = _flatten_tree_to_units(tree)
            if not units:
                raise RuntimeError("PageIndex returned no usable units.")

            if doc_key:
                doc_id = stable_doc_id_from_doc_key(doc_key)
            else:
                doc_id = stable_doc_id_from_source_path(input_path)

            store.reindex_doc(
                doc_id=doc_id,
                source_path=input_path,
                source_type=source_type,
                units=units,
            )
            docs_written.append(
                {
                    "doc_id": doc_id,
                    "section_code": str(manual_code),
                    "section_title": "Manual",
                    "unit_count": len(units),
                    "is_parent": True,
                }
            )
            unit_count = len(units)
            units_preview = [
                {
                    "unit_type": u.unit_type,
                    "unit_no": u.unit_no,
                    "title": u.title,
                    "heading_path": u.heading_path,
                    "summary": u.summary,
                    "text_preview": u.text[:280],
                }
                for u in units[: max(1, preview_units_limit)]
            ]
    finally:
        conn.close()

    payload: dict[str, Any] = {
        "doc_id": doc_id,
        "doc_key": doc_key,
        "source_path": input_path,
        "source_type": source_type,
        "unit_count": unit_count,
        "split_top_level_docs": split_top_level_docs,
        "manual_code": manual_code,
        "documents_written": docs_written,
        "tree_preview": _tree_preview(tree),
        "units_preview": units_preview,
    }
    if include_tree_json:
        payload["tree_json"] = tree

    return payload

