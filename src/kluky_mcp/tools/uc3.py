"""Record-management tools backed by the PostgreSQL repair schema."""

import csv
import subprocess
from datetime import datetime
from io import StringIO
from pathlib import Path

from fastmcp import FastMCP

from kluky_mcp.db import get_db_connection
from kluky_mcp.models import (
    AddRecordIfNotExistsInput,
    ExportAllRecordsToCsvDesktopInput,
    GetAllRecordsForNameInput,
    UpdateRecordInput,
)


def _get_desktop_dir() -> Path:
    """Best-effort resolution of the user's Desktop directory."""
    home = Path.home()

    try:
        result = subprocess.run(
            ["xdg-user-dir", "DESKTOP"],
            capture_output=True,
            text=True,
            check=False,
        )
        candidate = result.stdout.strip()
        if candidate:
            path = Path(candidate).expanduser()
            if path.is_absolute():
                path.mkdir(parents=True, exist_ok=True)
                return path
    except Exception:
        pass

    desktop = home / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    return desktop
def _build_all_records_csv(cur) -> str:
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
            p.name AS what_i_am_fixing,
            rl.work_desc,
            rl.faults,
            rl.raw_data,
            COALESCE(
                string_agg(DISTINCT res.name, ', ' ORDER BY res.name)
                    FILTER (WHERE res.id IS NOT NULL),
                ''
            ) AS repaired_with
        FROM users u
        JOIN repair_records rr
          ON rr.user_id = u.id
        JOIN items i
          ON i.id = rr.item_id
        LEFT JOIN repair_logs rl
          ON rl.record_id = rr.id
        LEFT JOIN parts p
          ON p.id = rl.part_id
        LEFT JOIN repair_log_tools rlt
          ON rlt.log_id = rl.id
        LEFT JOIN resources res
          ON res.id = rlt.tool_id
        GROUP BY
            rr.id,
            rl.id,
            u.first_name,
            u.last_name,
            i.name,
            rr.first_mention,
            rr.last_update,
            rl.dt,
            p.name,
            rl.work_desc,
            rl.faults,
            rl.raw_data
        ORDER BY
            COALESCE(rl.dt, rr.last_update) DESC,
            rr.id DESC,
            rl.id DESC
        """
    )

    rows = cur.fetchall()

    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow([
        "record_id",
        "log_id",
        "first_name",
        "last_name",
        "subject_name",
        "first_mention",
        "last_update",
        "dt",
        "what_i_am_fixing",
        "work_desc",
        "faults",
        "raw_data",
        "repaired_with",
    ])

    for row in rows:
        writer.writerow([
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5].isoformat() if row[5] else "",
            row[6].isoformat() if row[6] else "",
            row[7].isoformat() if row[7] else "",
            row[8] or "",
            row[9] or "",
            row[10] or "",
            row[11] or "",
            row[12] or "",
        ])

    return buffer.getvalue()
def _normalize_label(value: str | None) -> str:
    """Trim, collapse spaces, capitalize each word."""
    text = " ".join((value or "").split())
    if not text:
        return ""
    return " ".join(word[:1].upper() + word[1:].lower() for word in text.split(" "))


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
    first_name = _normalize_label(first_name)
    last_name = _normalize_label(last_name)
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
    subject_name = _normalize_label(subject_name)
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
    part_id: int,
    work_desc: str,
    raw_data: str,
) -> int:
    """Insert a new repair_logs row and return its ID."""
    cur.execute(
        """
        INSERT INTO repair_logs (record_id,part_id, work_desc, raw_data)
        VALUES (%s, %s, %s,%s)
        RETURNING id
        """,
        (record_id, part_id, work_desc, raw_data),
    )
    return cur.fetchone()[0]


def _update_repair_log(
    cur,
    record_id: int,
    log_id: int,
    part_id: int,
    work_desc: str,
    raw_data: str,
) -> int:
    """Update an existing repair_logs row and return its ID."""
    cur.execute(
        """
        UPDATE repair_logs
        SET record_id = %s,
            part_id = %s,
            work_desc = %s,
            raw_data = %s
        WHERE id = %s
        RETURNING id
        """,
        (record_id, part_id, work_desc, raw_data, log_id),
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
        SELECT id, name
        FROM resources
        WHERE deleted = false
          AND name = ANY(%s)
        """,
        (cleaned,),
    )
    rows = cur.fetchall()

    name_to_id = {name: tool_id for tool_id, name in rows}
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


def _get_or_create_part_id(cur, item_id: int, part_name: str) -> int:
    """
    Create (or reuse) a part for the given item, return parts.id.
    parts unique constraint: (item_id, name)
    """
    part_name_clean = _normalize_label(part_name)
    part_name_clean = part_name.strip()

    cur.execute(
        """
        INSERT INTO parts (item_id, name)
        VALUES (%s, %s)
        ON CONFLICT (item_id, name) DO NOTHING
        RETURNING id
        """,
        (item_id, part_name_clean),
    )
    row = cur.fetchone()
    if row is not None:
        return row[0]

    cur.execute(
        """
        SELECT id
        FROM parts
        WHERE item_id = %s
          AND name = %s
        LIMIT 1
        """,
        (item_id, part_name_clean),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("part lookup failed after conflict")
    return row[0]


def register(mcp: FastMCP) -> None:
    """Register UC3 record-management tools."""

    @mcp.tool(
        name="add_record_if_not_exists",
        annotations={
            "title": "Add Record If Not Exists",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    def add_record_if_not_exists(params: AddRecordIfNotExistsInput) -> str:
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
                part_id = _get_or_create_part_id(cur, item_id, params.what_i_am_fixing)
                log_id = _insert_repair_log(
                    cur,
                    record_id=record_id,
                    part_id=part_id,
                    work_desc=params.raw_text.strip(),
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
        name="get_all_records_for_name",
        annotations={
            "title": "Get All Records For Name",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def get_all_records_for_name(
        params: GetAllRecordsForNameInput,
    ) -> list[dict[str, object]]:
        """
        Return all repair log entries for all users with the exact same first/last name.
        Each returned item represents one repair_logs row (or a header-only record if no log exists).
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                first_name = _normalize_label(params.first_name)
                last_name = _normalize_label(params.last_name)
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
                        p.name AS part_name,
                        rl.work_desc,
                        rl.faults,
                        rl.raw_data,
                        COALESCE(
                            array_agg(DISTINCT res.name ORDER BY res.name)
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
                    LEFT JOIN parts p
                    ON p.id = rl.part_id
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
                        p.name,
                        rl.work_desc,
                        rl.faults,
                        rl.raw_data
                    ORDER BY
                        COALESCE(rl.dt, rr.last_update) DESC,
                        rr.id DESC,
                        rl.id DESC
                    """,
                    (first_name, last_name),
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
                            "work_desc": row[9] or "",
                            "faults": row[10],
                            "raw_data": row[11] or "",
                            "repaired_with": list(row[12] or []),
                        }
                    )

                return result
        except Exception:
            return []
        finally:
            conn.close()

    @mcp.tool(
        name="update_record",
        annotations={
            "title": "Update Record",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    def update_record(params: UpdateRecordInput) -> str:
        """
        Update an existing repair_logs row for an existing repair_records header.

        record_id is expected to be repair_records.id.
        log_id is expected to be repair_logs.id.

        On update:
        - new work_desc = previous work_desc + "\\n" + params.raw_text
        - new raw_data  = previous raw_data  + "\\n" + params.raw_text
        """
        try:
            record_id = int(params.record_id)
        except (TypeError, ValueError):
            return "update sa nepodaril"

        try:
            log_id = int(params.log_id)
        except (TypeError, ValueError):
            return "update sa nepodaril"

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        rl.work_desc,
                        rl.raw_data,
                        rr.item_id
                    FROM repair_logs rl
                    JOIN repair_records rr
                    ON rr.id = rl.record_id
                    WHERE rl.id = %s
                    AND rl.record_id = %s
                    LIMIT 1
                    """,
                    (log_id, record_id),
                )
                row = cur.fetchone()

                if row is None:
                    return "update sa nepodaril"

                previous_work_desc = row[0] or ""
                previous_raw_data = row[1] or ""
                item_id = row[2]

                appended_work_desc = _append_text(
                    previous_work_desc,
                    params.raw_text,
                )
                appended_raw_data = _append_text(
                    previous_raw_data,
                    params.raw_text,
                )

                part_id = _get_or_create_part_id(
                    cur,
                    item_id,
                    params.what_i_am_fixing,
                )

                log_id = _update_repair_log(
                    cur,
                    record_id=record_id,
                    log_id=log_id,
                    part_id=part_id,
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
    @mcp.tool(
        name="export_all_records_to_csv_desktop",
        annotations={
            "title": "Export All Records To CSV Desktop",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    def export_all_records_to_csv_desktop(
        params: ExportAllRecordsToCsvDesktopInput,
    ) -> str:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                csv_content = _build_all_records_csv(cur)

            desktop_dir = _get_desktop_dir()

            if params.filename:
                filename = params.filename
            else:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"servisne_zaznamy_{ts}.csv"

            if not filename.lower().endswith(".csv"):
                filename = f"{filename}.csv"

            file_path = desktop_dir / filename
            file_path.write_text(csv_content, encoding="utf-8-sig", newline="")

            return str(file_path)
        finally:
            conn.close()
