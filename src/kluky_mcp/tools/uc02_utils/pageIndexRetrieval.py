from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

from psycopg2.extensions import connection as PgConnection

_DIACRITIC_SOURCE = "áäčďéěíĺľňóôŕšťúýžÁÄČĎÉĚÍĹĽŇÓÔŔŠŤÚÝŽ"
_DIACRITIC_TARGET = "aacdeeillnoorstuyzaacdeeillnoorstuyz"


def _normalize_query_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_like = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    ascii_like = ascii_like.lower()
    return re.sub(r"[^a-z0-9]+", " ", ascii_like).strip()


def _build_search_query(
    query: str,
    normalized_tokens: list[str],
    top_k: int,
    manual_doc_id: str | None,
) -> tuple[str, tuple[Any, ...]]:
    query_params: list[Any] = [
        query,
        _DIACRITIC_SOURCE,
        _DIACRITIC_TARGET,
        _DIACRITIC_SOURCE,
        _DIACRITIC_TARGET,
        _DIACRITIC_SOURCE,
        _DIACRITIC_TARGET,
        query,
        query,
    ]

    manual_filter_sql = ""
    if manual_doc_id:
        manual_filter_sql = "and (doc_id = %s or doc_id like %s)"
        query_params.extend([manual_doc_id, f"{manual_doc_id}::%"])

    token_filters: list[str] = []
    for token in normalized_tokens:
        token_filters.append("normalized_blob like %s")
        query_params.append(f"%{token}%")

    token_or_sql = " or ".join(token_filters)
    token_gate_sql = f"or ({token_or_sql})" if token_or_sql else ""

    query_params.append(max(top_k * 40, 200))

    sql = f"""
        with prepared as (
            select
              id,
              doc_id,
              source_path,
              source_type,
              title,
              heading_path,
              summary,
              unit_no,
              text,
              ts_rank_cd(
                to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(summary, '')),
                plainto_tsquery('simple', %s)
              ) as ft_score,
              lower(regexp_replace(translate(coalesce(title, ''), %s, %s), '[^a-z0-9]+', ' ', 'g')) as normalized_title,
              lower(regexp_replace(translate(coalesce(summary, ''), %s, %s), '[^a-z0-9]+', ' ', 'g')) as normalized_summary,
              lower(regexp_replace(translate(
                coalesce(title, '') || ' ' || coalesce(summary, ''),
                %s,
                %s
              ), '[^a-z0-9]+', ' ', 'g')) as normalized_blob
            from doc_units
            where 1=1
              {manual_filter_sql}
        )
        select
          id,
          doc_id,
          source_path,
          source_type,
          coalesce(title, source_path) as document_name,
          heading_path,
          unit_no,
          text,
          ft_score,
          normalized_title,
          normalized_summary,
          normalized_blob,
          (
            to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(summary, ''))
            @@ plainto_tsquery('simple', %s)
          ) as ft_match
        from prepared
        where (
            to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(summary, ''))
            @@ plainto_tsquery('simple', %s)
        )
          {token_gate_sql}
        order by ft_score desc nulls last, id asc
        limit %s
    """
    return sql, tuple(query_params)


def _token_hits(value: str, tokens: list[str]) -> int:
    return sum(1 for token in tokens if token in value)


def _row_score(
    row: tuple[Any, ...],
    normalized_tokens: list[str],
    normalized_query: str,
) -> float:
    ft_score = float(row[8] or 0.0)
    normalized_title = str(row[9] or "")
    normalized_summary = str(row[10] or "")
    normalized_blob = str(row[11] or "")
    ft_match = bool(row[12])

    title_hits = _token_hits(normalized_title, normalized_tokens)
    summary_hits = _token_hits(normalized_summary, normalized_tokens)
    blob_hits = _token_hits(normalized_blob, normalized_tokens)

    phrase_bonus = 0.0
    if normalized_query:
        if normalized_query in normalized_title:
            phrase_bonus += 2.5
        if normalized_query in normalized_summary:
            phrase_bonus += 0.8

    return (
        (ft_score * 7.0)
        + (title_hits * 3.0)
        + (summary_hits * 2.0)
        + (min(blob_hits, 5) * 0.35)
        + phrase_bonus
        + (1.0 if ft_match else 0.0)
    )


def _aggregate_doc_scores(
    rows: list[tuple[Any, ...]],
    normalized_tokens: list[str],
    normalized_query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    doc_scores: dict[str, dict[str, Any]] = {}

    for row in rows:
        doc_id = str(row[1])
        parent_id, section_code = _parse_doc_id_hierarchy(doc_id)
        text_snippet = str(row[7] or "").replace("\n", " ").strip()[:400]
        row_score = _row_score(row, normalized_tokens, normalized_query)

        existing = doc_scores.get(doc_id)
        if existing is None:
            doc_scores[doc_id] = {
                "doc_id": doc_id,
                "manual_doc_id": parent_id,
                "section_code": section_code,
                "document_name": row[4],
                "source_path": row[2],
                "source_type": row[3],
                "matched_units": 1,
                "total_score": row_score,
                "best_row_score": row_score,
                "best_heading_path": row[5],
                "best_unit_no": row[6],
                "snippet": text_snippet,
                "search_mode": "hybrid_ranked",
            }
            continue

        existing["matched_units"] = int(existing["matched_units"]) + 1
        existing["total_score"] = float(existing["total_score"]) + row_score
        if row_score > float(existing["best_row_score"]):
            existing["best_row_score"] = row_score
            existing["best_heading_path"] = row[5]
            existing["best_unit_no"] = row[6]
            existing["snippet"] = text_snippet

    results = list(doc_scores.values())
    for item in results:
        matched_units = int(item["matched_units"])
        best_row_score = float(item["best_row_score"])
        total_score = float(item["total_score"])
        final_score = (
            (best_row_score * 0.72)
            + (total_score * 0.28)
            + (min(matched_units, 5) * 0.2)
        )
        item["score"] = round(final_score, 6)
        del item["best_row_score"]
        del item["total_score"]

    results.sort(
        key=lambda x: (float(x["score"]), int(x["matched_units"])), reverse=True
    )
    return results[:top_k]


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


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
            updated_at = row[6]
            if isinstance(updated_at, datetime):
                updated_at_value = updated_at.isoformat()
            else:
                updated_at_value = str(updated_at) if updated_at is not None else None

            documents.append(
                {
                    "doc_id": row[0],
                    "document_name": row[1],
                    "summary": row[2],
                    "source_path": row[3],
                    "source_type": row[4],
                    "unit_count": int(row[5]),
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
            group["manual_name"] = d["document_name"]
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


def fetch_document_text(
    pg_conn: PgConnection,
    *,
    doc_id: str,
    document_name: str | None = None,
    unit_no: int | None = None,
) -> dict[str, Any]:
    meta_query = """
        select
          doc_id,
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
        cur.execute(meta_query, (doc_id,))
        meta = cur.fetchone()

    if not meta:
        raise RuntimeError(f"Dokument s doc_id '{doc_id}' neexistuje.")

    db_name = meta[1] or ""
    if document_name is not None and _normalize_name(document_name) != _normalize_name(
        db_name
    ):
        raise RuntimeError(
            "Nazov dokumentu nesedi k doc_id. "
            f"Ocakavane '{db_name}', prislo '{document_name}'."
        )

    if unit_no is None:
        units_query = """
            select unit_type, unit_no, text
            from doc_units
            where doc_id = %s
            order by
              case when unit_no is null then 2147483647 else unit_no end asc,
              id asc
        """
        units_query_params: tuple[Any, ...] = (doc_id,)
    else:
        units_query = """
            select unit_type, unit_no, text
            from doc_units
            where doc_id = %s
              and unit_no = %s
            order by id asc
        """
        units_query_params = (doc_id, unit_no)

    units: list[dict[str, Any]] = []
    with pg_conn.cursor() as cur:
        cur.execute(units_query, units_query_params)
        rows = cur.fetchall()

    if unit_no is not None and not rows:
        raise RuntimeError(f"Dokument s doc_id '{doc_id}' nema unit_no '{unit_no}'.")

    for unit_type, unit_no, text in rows:
        units.append(
            {
                "unit_type": unit_type,
                "unit_no": unit_no,
                "text": text,
            }
        )

    merged_text = "\n\n".join(
        f"[unit_type={u['unit_type']}; unit_no={u['unit_no']}]\n{u['text']}"
        for u in units
    )

    return {
        "doc_id": doc_id,
        "unit_no": unit_no,
        "document_name": db_name,
        "summary": meta[2],
        "source_path": meta[3],
        "source_type": meta[4],
        "unit_count": len(units),
        "text": merged_text,
    }

