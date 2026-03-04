"""Record-management tools backed by the PostgreSQL repair schema."""

from fastmcp import FastMCP

from kluky_mcp.constants import TOOL_NAMESPACE
from kluky_mcp.db import get_db_connection
from kluky_mcp.models import (
    AddRecordIfNotExistsInput,
    GetAllRecordsForNameInput,
    UpdateRecordInput,
)


def _append_text(previous: str | None, new_value: str) -> str:
    """Append new text to previous text separated by a newline."""
    previous_clean = (previous or "").strip()
    new_clean = new_value.strip()

    if not previous_clean:
        return new_clean
    if not new_clean:
        return previous_clean
    return f"{previous_clean}\n{new_clean}"


def _get_or_create_user_id(cur, first_name: str, last_name: str) -> int:
    """Find an existing user by exact first/last name, or create one."""
    cur.execute(
        """
        SELECT id
        FROM users
        WHERE first_name = %s
          AND last_name = %s
        ORDER BY id
        LIMIT 1
        """,
        (first_name, last_name),
    )
    row = cur.fetchone()
    if row is not None:
        return row[0]

    cur.execute(
        """
        INSERT INTO users (first_name, last_name)
        VALUES (%s, %s)
        RETURNING id
        """,
        (first_name, last_name),
    )
    return cur.fetchone()[0]


def _get_or_create_item_id(cur, subject_name: str) -> int:
    """Find an existing item by name (with NULL code), or create one."""
    cur.execute(
        """
        SELECT id
        FROM items
        WHERE name = %s
          AND code IS NULL
        ORDER BY id
        LIMIT 1
        """,
        (subject_name,),
    )
    row = cur.fetchone()
    if row is not None:
        return row[0]

    cur.execute(
        """
        INSERT INTO items (name, code)
        VALUES (%s, NULL)
        RETURNING id
        """,
        (subject_name,),
    )
    return cur.fetchone()[0]


def _get_or_create_repair_record_id(cur, user_id: int, item_id: int) -> int:
    """
    Ensure the repair_records header exists for (user_id, item_id).
    Returns the existing or newly created repair_records.id.
    """
    cur.execute(
        """
        INSERT INTO repair_records (user_id, item_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id, item_id) DO NOTHING
        RETURNING id
        """,
        (user_id, item_id),
    )
    row = cur.fetchone()
    if row is not None:
        return row[0]

    cur.execute(
        """
        SELECT id
        FROM repair_records
        WHERE user_id = %s
          AND item_id = %s
        LIMIT 1
        """,
        (user_id, item_id),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("repair_record lookup failed after conflict")
    return row[0]


def _insert_repair_log(
    cur,
    record_id: int,
    work_desc: str,
    raw_data: str,
) -> int:
    """Insert a new repair_logs row and return its ID."""
    cur.execute(
        """
        INSERT INTO repair_logs (record_id, work_desc, raw_data)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (record_id, work_desc, raw_data),
    )
    return cur.fetchone()[0]


def _normalize_tool_names(tool_names: list[str]) -> list[str]:
    """Strip, remove empties, and deduplicate while preserving order."""
    cleaned: list[str] = []
    seen: set[str] = set()

    for name in tool_names or []:
        value = name.strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)

    return cleaned


def _get_existing_tool_ids(cur, tool_names: list[str]) -> list[int]:
    """
    Resolve tool names to resources.id.
    Only existing, non-deleted resources are returned.
    Unknown tool names are ignored.
    """
    cleaned = _normalize_tool_names(tool_names)
    if not cleaned:
        return []

    cur.execute(
        """
        SELECT id, nazov
        FROM resources
        WHERE deleted = false
          AND nazov = ANY(%s)
        """,
        (cleaned,),
    )
    rows = cur.fetchall()

    name_to_id = {nazov: tool_id for tool_id, nazov in rows}
    return [name_to_id[name] for name in cleaned if name in name_to_id]


def _attach_tools_to_log(cur, log_id: int, tool_ids: list[int]) -> None:
    """Attach resolved tools to a repair log."""
    for tool_id in tool_ids:
        cur.execute(
            """
            INSERT INTO repair_log_tools (log_id, tool_id)
            VALUES (%s, %s)
            ON CONFLICT (log_id, tool_id) DO NOTHING
            """,
            (log_id, tool_id),
        )


def register(mcp: FastMCP) -> None:
    """Register UC3 record-management tools."""

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_add_record_if_not_exists",
        annotations={
            "title": "Add Record If Not Exists",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    def kluky_add_record_if_not_exists(params: AddRecordIfNotExistsInput) -> str:
        """
        Create (or reuse) the repair_records header for user+item
        and add a new repair_logs row.

        On create:
        - work_desc = params.what_i_am_fixing
        - raw_data = params.raw_text
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                user_id = _get_or_create_user_id(
                    cur,
                    params.first_name,
                    params.last_name,
                )
                item_id = _get_or_create_item_id(cur, params.subject_name)
                record_id = _get_or_create_repair_record_id(cur, user_id, item_id)

                log_id = _insert_repair_log(
                    cur,
                    record_id=record_id,
                    work_desc=params.what_i_am_fixing.strip(),
                    raw_data=params.raw_text.strip(),
                )

                tool_ids = _get_existing_tool_ids(cur, params.repaired_with)
                _attach_tools_to_log(cur, log_id, tool_ids)

                conn.commit()
                return "pridal som"
        except Exception:
            conn.rollback()
            return "nepridal som"
        finally:
            conn.close()

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_get_all_records_for_name",
        annotations={
            "title": "Get All Records For Name",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kluky_get_all_records_for_name(
        params: GetAllRecordsForNameInput,
    ) -> list[dict[str, object]]:
        """
        Return all repair log entries for all users with the exact same first/last name.
        Each returned item represents one repair_logs row (or a header-only record if no log exists).
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        rr.id AS record_id,
                        rl.id AS log_id,
                        u.first_name,
                        u.last_name,
                        i.name AS subject_name,
                        rr.first_mention,
                        rr.last_update,
                        rl.dt,
                        rl.work_desc,
                        rl.faults,
                        rl.raw_data,
                        COALESCE(
                            array_agg(DISTINCT res.nazov ORDER BY res.nazov)
                                FILTER (WHERE res.id IS NOT NULL),
                            ARRAY[]::text[]
                        ) AS repaired_with
                    FROM users u
                    JOIN repair_records rr
                      ON rr.user_id = u.id
                    JOIN items i
                      ON i.id = rr.item_id
                    LEFT JOIN repair_logs rl
                      ON rl.record_id = rr.id
                    LEFT JOIN repair_log_tools rlt
                      ON rlt.log_id = rl.id
                    LEFT JOIN resources res
                      ON res.id = rlt.tool_id
                    WHERE u.first_name = %s
                      AND u.last_name = %s
                    GROUP BY
                        rr.id,
                        rl.id,
                        u.first_name,
                        u.last_name,
                        i.name,
                        rr.first_mention,
                        rr.last_update,
                        rl.dt,
                        rl.work_desc,
                        rl.faults,
                        rl.raw_data
                    ORDER BY
                        COALESCE(rl.dt, rr.last_update) DESC,
                        rr.id DESC,
                        rl.id DESC
                    """,
                    (params.first_name, params.last_name),
                )

                rows = cur.fetchall()
                result: list[dict[str, object]] = []

                for row in rows:
                    result.append(
                        {
                            "record_id": row[0],
                            "log_id": row[1],
                            "first_name": row[2],
                            "last_name": row[3],
                            "subject_name": row[4],
                            "first_mention": row[5].isoformat() if row[5] else None,
                            "last_update": row[6].isoformat() if row[6] else None,
                            "dt": row[7].isoformat() if row[7] else None,
                            "what_i_am_fixing": row[8] or "",
                            "faults": row[9],
                            "raw_data": row[10] or "",
                            "repaired_with": list(row[11] or []),
                        }
                    )

                return result
        except Exception:
            return []
        finally:
            conn.close()

    @mcp.tool(
        name=f"{TOOL_NAMESPACE}_update_record",
        annotations={
            "title": "Update Record",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    def kluky_update_record(params: UpdateRecordInput) -> str:
        """
        Append a new repair_logs row to an existing repair_records header.

        record_id is expected to be repair_records.id.

        On update:
        - new work_desc = previous latest work_desc + "\\n" + params.what_i_am_fixing
        - new raw_data  = previous latest raw_data  + "\\n" + params.raw_text
        """
        try:
            record_id = int(params.record_id)
        except (TypeError, ValueError):
            return "update sa nepodaril"

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM repair_records
                    WHERE id = %s
                    """,
                    (record_id,),
                )
                if cur.fetchone() is None:
                    return "update sa nepodaril"

                cur.execute(
                    """
                    SELECT work_desc, raw_data
                    FROM repair_logs
                    WHERE record_id = %s
                    ORDER BY dt DESC, id DESC
                    LIMIT 1
                    """,
                    (record_id,),
                )
                row = cur.fetchone()

                previous_work_desc = row[0] if row else ""
                previous_raw_data = row[1] if row else ""

                appended_work_desc = _append_text(
                    previous_work_desc,
                    params.what_i_am_fixing,
                )
                appended_raw_data = _append_text(
                    previous_raw_data,
                    params.raw_text,
                )

                log_id = _insert_repair_log(
                    cur,
                    record_id=record_id,
                    work_desc=appended_work_desc,
                    raw_data=appended_raw_data,
                )

                tool_ids = _get_existing_tool_ids(cur, params.repaired_with)
                _attach_tools_to_log(cur, log_id, tool_ids)

                conn.commit()
                return "update sa podaril"
        except Exception:
            conn.rollback()
            return "update sa nepodaril"
        finally:
            conn.close()