from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from pageindex import config, page_index_main
from pageindex.page_index_md import md_to_tree
from PyPDF2 import PdfReader

from kluky_mcp.db import get_db_connection
from kluky_mcp.settings import settings

from .pageIndexUtils import (
    DocUnit,
    PageIndexStore,
    convert_to_markdown,
    stable_doc_id_from_doc_key,
    stable_doc_id_from_source_path,
)


def _ensure_openai_env() -> None:
    custom_key = os.getenv("open_ai_api_key", "").strip() or settings.open_ai_api_key
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    effective_key = custom_key or openai_key
    if not effective_key:
        raise RuntimeError("Missing API key. Set open_ai_api_key or OPENAI_API_KEY.")

    os.environ.setdefault("open_ai_api_key", effective_key)
    os.environ.setdefault("CHATGPT_API_KEY", effective_key)
    os.environ.setdefault("OPENAI_API_KEY", effective_key)

    base_url = (
        os.getenv("open_ai_api_base", "").strip()
        or settings.open_ai_api_base
        or os.getenv("OPENAI_BASE_URL", "").strip()
    )
    if base_url:
        os.environ.setdefault("open_ai_api_base", base_url)
        os.environ.setdefault("OPENAI_BASE_URL", base_url)
        os.environ.setdefault("OPENAI_API_BASE", base_url)


def _run_pageindex_document(input_path: str) -> dict[str, Any]:
    src = Path(input_path)
    if not src.exists():
        raise RuntimeError(f"Input file does not exist: {input_path}")

    _ensure_openai_env()

    model_name = os.getenv("PAGEINDEX_MODEL", "").strip() or settings.pageindex_model

    opt = config(
        model=model_name,
        toc_check_page_num=20,
        max_page_num_each_node=10,
        max_token_num_each_node=20000,
        if_add_node_id="yes",
        if_add_node_summary="yes",
        if_add_doc_description="no",
        if_add_node_text="yes",
    )

    ext = src.suffix.lower()
    md_path = src
    temp_md_path: Path | None = None

    if ext == ".pdf":
        source_arg = "--pdf_path"
    elif ext in {".md", ".markdown"}:
        source_arg = "--md_path"
    else:
        md_text = convert_to_markdown(str(src.resolve()))
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(md_text)
            tmp.flush()
        temp_md_path = Path(tmp.name)
        md_path = temp_md_path
        source_arg = "--md_path"

    try:
        if source_arg == "--pdf_path":
            try:
                tree_payload = page_index_main(str(md_path.resolve()), opt)
            except Exception as exc:
                error_text = str(exc)
                if "page_index_given_in_toc" not in error_text:
                    raise

                fallback_opt = config(
                    model=model_name,
                    toc_check_page_num=0,
                    max_page_num_each_node=10,
                    max_token_num_each_node=20000,
                    if_add_node_id="yes",
                    if_add_node_summary="yes",
                    if_add_doc_description="no",
                    if_add_node_text="yes",
                )
                tree_payload = page_index_main(str(md_path.resolve()), fallback_opt)
        else:
            tree_payload = asyncio.run(
                md_to_tree(
                    md_path=str(md_path.resolve()),
                    if_thinning=False,
                    if_add_node_summary="yes",
                    model=model_name,
                    if_add_doc_description="no",
                    if_add_node_text="yes",
                    if_add_node_id="yes",
                )
            )

        if isinstance(tree_payload, list):
            tree_payload = {
                "doc_name": md_path.stem,
                "structure": [node for node in tree_payload if isinstance(node, dict)],
            }

        if not isinstance(tree_payload, dict):
            raise RuntimeError("Local PageIndex output is not a JSON object.")

        tree_payload.setdefault("pageindex_doc_id", f"local:{md_path.stem}")
        return tree_payload
    finally:
        if temp_md_path is not None and temp_md_path.exists():
            temp_md_path.unlink()


def _parse_nonnegative_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        raw = value.strip()
        if raw.isdigit():
            parsed = int(raw)
            return parsed if parsed >= 0 else None
        match = re.search(r"\d+", raw)
        if match:
            parsed = int(match.group(0))
            return parsed if parsed >= 0 else None
    return None


def _extract_page_from_text(node: dict[str, Any]) -> int | None:
    text_value = node.get("text")
    if not isinstance(text_value, str) or not text_value.strip():
        return None

    match = re.search(r"^\s*(\d{1,5})(?:\s|$)", text_value)
    if not match:
        return None

    page = int(match.group(1))
    return page if page > 0 else None


def _extract_page_range(node: dict[str, Any]) -> tuple[int | None, int | None]:
    page_start = None
    page_end = None

    direct_start_keys = (
        "page_start",
        "start_page",
        "page_from",
        "first_page",
        "start_index",
        "physical_index",
        "physical_page",
    )
    direct_end_keys = (
        "page_end",
        "end_page",
        "page_to",
        "last_page",
        "end_index",
    )
    single_page_keys = (
        "page",
        "page_no",
        "page_num",
        "page_number",
        "page_index",
    )

    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}

    def get_value(key: str) -> object:
        if key in node:
            return node.get(key)
        return metadata.get(key)

    for key in direct_start_keys:
        value = _parse_nonnegative_int(get_value(key))
        if value is not None:
            page_start = value
            break

    for key in direct_end_keys:
        value = _parse_nonnegative_int(get_value(key))
        if value is not None:
            page_end = value
            break

    if page_start is None and page_end is None:
        for key in single_page_keys:
            value = _parse_nonnegative_int(get_value(key))
            if value is not None:
                page_start = value
                page_end = value
                break

    pages = node.get("pages") or metadata.get("pages")
    if page_start is None and page_end is None and isinstance(pages, list):
        parsed_pages = sorted(
            p for p in (_parse_nonnegative_int(item) for item in pages) if p is not None
        )
        if parsed_pages:
            page_start = parsed_pages[0]
            page_end = parsed_pages[-1]

    if page_start is None and page_end is None:
        text_page = _extract_page_from_text(node)
        if text_page is not None:
            page_start = text_page
            page_end = text_page

    if page_start is None and page_end is not None:
        page_start = page_end
    if page_end is None and page_start is not None:
        page_end = page_start

    if page_start is not None and page_end is not None and page_start > page_end:
        page_start, page_end = page_end, page_start

    return page_start, page_end


def _format_page_range(page_start: int | None, page_end: int | None) -> str | None:
    if page_start is None and page_end is None:
        return None
    if page_start is None:
        return str(page_end)
    if page_end is None:
        return str(page_start)
    if page_start == page_end:
        return str(page_start)
    return f"{page_start}-{page_end}"


def _node_text_payload(node: dict[str, Any]) -> str:
    title = str(node.get("title") or "").strip()
    text_value = str(node.get("text") or "").strip()

    if not text_value and node.get("summary"):
        text_value = str(node["summary"]).strip()

    page_start, page_end = _extract_page_range(node)
    page_range = _format_page_range(page_start, page_end)

    parts: list[str] = []
    if title:
        parts.append(f"# {title}")
    if text_value:
        parts.append(text_value)
    if page_range:
        parts.append(f"[Pages: {page_range}]")
    return "\n\n".join(parts).strip()


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
        summary = _short_summary(raw_summary)
    else:
        summary = _short_summary(payload_text)

    page_start, page_end = _extract_page_range(node)
    page_range = _format_page_range(page_start, page_end)
    if page_range and summary:
        return f"{summary} [str. {page_range}]"
    if page_range:
        return f"[str. {page_range}]"
    return summary


def _flatten_tree_to_units(
    tree: dict[str, Any], *, min_text_len: int = 20
) -> list[DocUnit]:
    units: list[DocUnit] = []

    def visit(node: dict[str, Any], path: list[str]) -> None:
        title = str(node.get("title") or "").strip()
        next_path = [*path]
        if title:
            next_path.append(title)

        payload = _node_text_payload(node)
        if len(payload.strip()) >= min_text_len:
            page_start, page_end = _extract_page_range(node)
            heading_path = " > ".join(next_path) if next_path else None
            units.append(
                DocUnit(
                    unit_type="section",
                    unit_no=len(units) + 1,
                    start_page=page_start,
                    end_page=page_end,
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


def _heading_parts(heading_path: str | None) -> list[str]:
    if not heading_path:
        return []
    return [part.strip() for part in heading_path.split(">") if part.strip()]


def _is_merge_compatible(target: DocUnit, source: DocUnit) -> bool:
    target_parts = _heading_parts(target.heading_path)
    source_parts = _heading_parts(source.heading_path)
    if not target_parts or not source_parts:
        return False

    target_parent = target_parts[:-1]
    source_parent = source_parts[:-1]
    if target_parent and source_parent and target_parent == source_parent:
        return True

    if (
        len(target_parts) <= len(source_parts)
        and source_parts[: len(target_parts)] == target_parts
    ):
        return True

    if (
        len(source_parts) <= len(target_parts)
        and target_parts[: len(source_parts)] == source_parts
    ):
        return True

    return False


def _refresh_unit_summary(unit: DocUnit) -> None:
    page_range = _format_page_range(unit.start_page, unit.end_page)
    summary = _short_summary(unit.text)
    if page_range and summary:
        unit.summary = f"{summary} [str. {page_range}]"
        return
    if page_range:
        unit.summary = f"[str. {page_range}]"
        return
    unit.summary = summary


def _merge_units(target: DocUnit, source: DocUnit, *, prepend: bool) -> None:
    if prepend:
        target.text = f"{source.text}\n\n{target.text}".strip()
    else:
        target.text = f"{target.text}\n\n{source.text}".strip()

    pages = [
        page
        for page in (
            target.start_page,
            target.end_page,
            source.start_page,
            source.end_page,
        )
        if page is not None
    ]
    if pages:
        target.start_page = min(pages)
        target.end_page = max(pages)

    _refresh_unit_summary(target)


def _merge_small_units(units: list[DocUnit], *, min_chars: int = 400) -> list[DocUnit]:
    if not units:
        return units

    kept: list[DocUnit] = []
    for unit in units:
        text_len = len(unit.text.strip())
        if text_len < min_chars and kept and _is_merge_compatible(kept[-1], unit):
            _merge_units(kept[-1], unit, prepend=False)
            continue
        kept.append(unit)

    if len(kept) <= 1:
        for index, unit in enumerate(kept, start=1):
            unit.unit_no = index
        return kept

    i = len(kept) - 2
    while i >= 0:
        unit = kept[i]
        text_len = len(unit.text.strip())
        if text_len < min_chars and _is_merge_compatible(kept[i + 1], unit):
            _merge_units(kept[i + 1], unit, prepend=True)
            del kept[i]
        i -= 1

    for index, unit in enumerate(kept, start=1):
        unit.unit_no = index
    return kept


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
        }

    return {
        "title": tree.get("title"),
        "node_id": tree.get("node_id"),
        "children_count": len(tree.get("nodes") or []),
    }


def _read_pdf_page_count(input_path: str) -> int | None:
    pdf_path = Path(input_path)
    if pdf_path.suffix.lower() != ".pdf":
        return None
    try:
        reader = PdfReader(str(pdf_path))
        return len(reader.pages)
    except Exception:
        return None


def _apply_page_count_fallback(units: list[DocUnit], page_count: int | None) -> None:
    if not units or page_count is None or page_count <= 0:
        return

    missing_all = all(u.start_page is None and u.end_page is None for u in units)
    if not missing_all:
        return

    if page_count == 1:
        for unit in units:
            unit.start_page = 1
            unit.end_page = 1
        return

    if len(units) == 1:
        units[0].start_page = 1
        units[0].end_page = page_count


def ingest_with_pageindex(
    input_path: str,
    *,
    doc_key: str | None = None,
    include_tree_json: bool = False,
    preview_units_limit: int = 3,
) -> dict[str, Any]:
    tree = _run_pageindex_document(input_path)
    source_type = Path(input_path).suffix.lower().lstrip(".") or "unknown"
    manual_name = Path(input_path).name

    doc_id = (
        stable_doc_id_from_doc_key(doc_key)
        if doc_key
        else stable_doc_id_from_source_path(input_path)
    )

    units = _flatten_tree_to_units(tree)
    if not units:
        raise RuntimeError("PageIndex returned no usable units.")

    units = _merge_small_units(units, min_chars=400)

    _apply_page_count_fallback(units, _read_pdf_page_count(input_path))

    conn = get_db_connection()
    store = PageIndexStore(conn)
    try:
        store.reindex_doc(
            doc_id=doc_id,
            manual_name=manual_name,
            source_path=input_path,
            source_type=source_type,
            units=units,
        )
    finally:
        conn.close()

    units_preview = [
        {
            "unit_type": u.unit_type,
            "unit_no": u.unit_no,
            "start_page": u.start_page,
            "end_page": u.end_page,
            "title": u.title,
            "heading_path": u.heading_path,
            "summary": u.summary,
            "text_preview": u.text[:280],
        }
        for u in units[: max(1, preview_units_limit)]
    ]

    payload: dict[str, Any] = {
        "doc_id": doc_id,
        "doc_key": doc_key,
        "pageindex_doc_id": tree.get("pageindex_doc_id"),
        "source_path": input_path,
        "manual_name": manual_name,
        "source_type": source_type,
        "unit_count": len(units),
        "documents_written": [
            {
                "doc_id": doc_id,
                "unit_count": len(units),
            }
        ],
        "tree_preview": _tree_preview(tree),
        "units_preview": units_preview,
    }
    if include_tree_json:
        payload["tree_json"] = tree

    return payload

