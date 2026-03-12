from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from psycopg2.extensions import connection as PgConnection


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _resolve_doc_id_by_manual_name(pg_conn: PgConnection, manual_name: str) -> str:
    normalized = _normalize_name(manual_name)
    query = """
        select doc_id
        from doc_units
        where lower(trim(
          coalesce(
            manual_name,
            regexp_replace(source_path, '^.*[\\/]', ''),
            source_path
          )
        )) = %s
        group by doc_id
        order by max(created_at) desc, doc_id asc
        limit 1
    """

    with pg_conn.cursor() as cur:
        cur.execute(query, (normalized,))
        row = cur.fetchone()

    if not row:
        raise RuntimeError(f"Manual '{manual_name}' neexistuje.")

    return str(row[0])


def _parse_doc_id_hierarchy(doc_id: str) -> tuple[str, str | None]:
    if "::" in doc_id:
        parent_id, child_code = doc_id.split("::", 1)
        return parent_id, child_code
    return doc_id, None


def _section_sort_key(section_code: str | None) -> tuple[int, ...]:
    if not section_code:
        return (10**9,)
    parts = re.findall(r"\d+", section_code)
    if not parts:
        return (10**9,)
    return tuple(int(p) for p in parts)


def fetch_document_library(pg_conn: PgConnection) -> dict[str, Any]:
    query = """
        select
          doc_id,
          coalesce(
            max(manual_name) filter (where manual_name is not null and manual_name <> ''),
            regexp_replace(max(source_path), '^.*[\\/]', ''),
            max(source_path)
          ) as manual_name,
          coalesce(
            max(title) filter (where title is not null and title <> ''),
            max(source_path)
          ) as document_name,
          max(summary) filter (where summary is not null and summary <> '') as summary,
          max(source_path) as source_path,
          max(source_type) as source_type,
          count(*) as unit_count,
          max(created_at) as updated_at
        from doc_units
        group by doc_id
        order by max(created_at) desc, doc_id asc
    """

    documents: list[dict[str, Any]] = []
    with pg_conn.cursor() as cur:
        cur.execute(query)
        for row in cur.fetchall():
            updated_at = row[7]
            if isinstance(updated_at, datetime):
                updated_at_value = updated_at.isoformat()
            else:
                updated_at_value = str(updated_at) if updated_at is not None else None

            documents.append(
                {
                    "doc_id": row[0],
                    "manual_name": row[1],
                    "document_name": row[2],
                    "summary": row[3],
                    "source_path": row[4],
                    "source_type": row[5],
                    "unit_count": int(row[6]),
                    "updated_at": updated_at_value,
                }
            )

    parent_groups: dict[str, dict[str, Any]] = {}
    ungrouped_documents: list[dict[str, Any]] = []

    for d in documents:
        parent_id, section_code = _parse_doc_id_hierarchy(d["doc_id"])
        group = parent_groups.get(parent_id)
        if group is None:
            group = {
                "manual_doc_id": parent_id,
                "manual_name": None,
                "source_path": None,
                "source_type": None,
                "updated_at": None,
                "unit_count": 0,
                "summary": None,
                "documents": [],
            }
            parent_groups[parent_id] = group

        if section_code is None:
            group["manual_name"] = d.get("manual_name") or d["document_name"]
            group["source_path"] = d["source_path"]
            group["source_type"] = d["source_type"]
            group["updated_at"] = d["updated_at"]
            group["unit_count"] = d["unit_count"]
            group["summary"] = d.get("summary")
        else:
            group["documents"].append(
                {
                    "doc_id": d["doc_id"],
                    "section_code": section_code,
                    "document_name": d["document_name"],
                    "summary": d.get("summary"),
                    "source_path": d["source_path"],
                    "source_type": d["source_type"],
                    "unit_count": d["unit_count"],
                    "updated_at": d["updated_at"],
                }
            )

    manuals: list[dict[str, Any]] = []
    for parent_id, group in parent_groups.items():
        children = group["documents"]
        if not children:
            ungrouped_documents.append(
                {
                    "doc_id": parent_id,
                    "document_name": group["manual_name"] or parent_id,
                    "summary": group.get("summary"),
                    "source_path": group["source_path"],
                    "source_type": group["source_type"],
                    "unit_count": int(group["unit_count"] or 0),
                    "updated_at": group["updated_at"],
                }
            )
            continue

        children.sort(key=lambda x: _section_sort_key(x.get("section_code")))

        manual_name = group["manual_name"]
        if not manual_name:
            first_code = children[0].get("section_code")
            manual_prefix = (
                first_code.split(".")[0]
                if first_code and "." in first_code
                else first_code
            )
            manual_name = (
                f"Manual {manual_prefix}"
                if manual_prefix
                else f"Manual {parent_id[:8]}"
            )

        manuals.append(
            {
                "manual_doc_id": parent_id,
                "manual_name": manual_name,
                "summary": group.get("summary") or children[0].get("summary"),
                "source_path": group["source_path"] or children[0].get("source_path"),
                "source_type": group["source_type"] or children[0].get("source_type"),
                "updated_at": group["updated_at"] or children[0].get("updated_at"),
                "unit_count": int(group["unit_count"] or 0),
                "documents_count": len(children),
                "documents": children,
            }
        )

    manuals.sort(
        key=lambda m: (m.get("updated_at") or "", m.get("manual_doc_id") or ""),
        reverse=True,
    )

    return {
        "count": len(documents),
        "documents": documents,
        "manuals_count": len(manuals),
        "manuals": manuals,
        "ungrouped_count": len(ungrouped_documents),
        "ungrouped_documents": ungrouped_documents,
    }


def fetch_document_units_catalog(pg_conn: PgConnection) -> list[dict[str, Any]]:
    query = """
        with doc_meta as (
          select
            doc_id,
            coalesce(
              max(manual_name) filter (where manual_name is not null and manual_name <> ''),
              regexp_replace(max(source_path), '^.*[\\/]', ''),
              max(source_path)
            ) as manual_name,
            coalesce(
              max(title) filter (where title is not null and title <> ''),
              max(source_path)
            ) as document_name,
            max(created_at) as updated_at
          from doc_units
          group by doc_id
        )
        select
          u.doc_id,
          m.manual_name,
          m.document_name,
          coalesce(nullif(u.title, ''), m.document_name, m.manual_name) as title,
          u.unit_no,
          u.start_page,
          u.end_page,
          coalesce(nullif(u.summary, ''), '') as summary,
          m.updated_at
        from doc_units u
        join doc_meta m on m.doc_id = u.doc_id
        order by
          m.updated_at desc,
          m.document_name asc,
          case when u.unit_no is null then 2147483647 else u.unit_no end asc,
          u.id asc
    """

    rows_payload: list[dict[str, Any]] = []
    with pg_conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    for row in rows:
        updated_at = row[8]
        if isinstance(updated_at, datetime):
            updated_at_value = updated_at.isoformat()
        else:
            updated_at_value = str(updated_at) if updated_at is not None else None

        rows_payload.append(
            {
                "doc_id": row[0],
                "manual_name": row[1],
                "document_name": row[2],
                "title": row[3],
                "unit_no": row[4],
                "start_page": row[5],
                "end_page": row[6],
                "summary": row[7],
                "updated_at": updated_at_value,
            }
        )

    return rows_payload


def fetch_document_text(
    pg_conn: PgConnection,
    *,
    doc_id: str | None = None,
    manual_name: str | None = None,
    document_name: str | None = None,
    unit_no: int | None = None,
) -> dict[str, Any]:
    resolved_doc_id = doc_id
    if not resolved_doc_id:
        if not manual_name:
            raise RuntimeError("Je potrebne zadat doc_id alebo manual_name.")
        resolved_doc_id = _resolve_doc_id_by_manual_name(pg_conn, manual_name)

    meta_query = """
        select
          doc_id,
          coalesce(
            max(manual_name) filter (where manual_name is not null and manual_name <> ''),
            regexp_replace(max(source_path), '^.*[\\/]', ''),
            max(source_path)
          ) as manual_name,
          coalesce(
            max(title) filter (where title is not null and title <> ''),
            max(source_path)
          ) as document_name,
          max(summary) filter (where summary is not null and summary <> '') as summary,
          max(source_path) as source_path,
          max(source_type) as source_type
        from doc_units
        where doc_id = %s
        group by doc_id
    """

    with pg_conn.cursor() as cur:
        cur.execute(meta_query, (resolved_doc_id,))
        meta = cur.fetchone()

    if not meta:
        raise RuntimeError(f"Dokument s doc_id '{resolved_doc_id}' neexistuje.")

    manual_name = meta[1] or ""
    db_name = meta[2] or ""
    if document_name is not None and _normalize_name(document_name) != _normalize_name(
        db_name
    ):
        raise RuntimeError(
            "Nazov dokumentu nesedi k doc_id. "
            f"Ocakavane '{db_name}', prislo '{document_name}'."
        )

    if unit_no is None:
        units_query = """
            select unit_type, unit_no, start_page, end_page, text
            from doc_units
            where doc_id = %s
            order by
              case when unit_no is null then 2147483647 else unit_no end asc,
              id asc
        """
        units_query_params: tuple[Any, ...] = (resolved_doc_id,)
    else:
        units_query = """
            select unit_type, unit_no, start_page, end_page, text
            from doc_units
            where doc_id = %s
              and unit_no = %s
            order by id asc
        """
        units_query_params = (resolved_doc_id, unit_no)

    units: list[dict[str, Any]] = []
    with pg_conn.cursor() as cur:
        cur.execute(units_query, units_query_params)
        rows = cur.fetchall()

    if unit_no is not None and not rows:
        raise RuntimeError(
            f"Dokument s doc_id '{resolved_doc_id}' nema unit_no '{unit_no}'."
        )

    for unit_type, unit_no, start_page, end_page, text in rows:
        units.append(
            {
                "unit_type": unit_type,
                "unit_no": unit_no,
                "start_page": start_page,
                "end_page": end_page,
                "text": text,
            }
        )

    merged_text = "\n\n".join(
        f"[unit_type={u['unit_type']}; unit_no={u['unit_no']}; start_page={u['start_page']}; end_page={u['end_page']}]\n{u['text']}"
        for u in units
    )

    return {
        "doc_id": resolved_doc_id,
        "unit_no": unit_no,
        "manual_name": manual_name,
        "document_name": db_name,
        "summary": meta[3],
        "source_path": meta[4],
        "source_type": meta[5],
        "unit_count": len(units),
        "text": merged_text,
    }
