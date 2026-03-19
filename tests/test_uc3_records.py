"""UC3 integration tests against the real database."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

import kluky_mcp.tools.uc3 as uc3_module
from kluky_mcp.db import get_db_connection
from kluky_mcp.models import (
    AddRecordIfNotExistsInput,
    ExportAllRecordsToCsvDesktopInput,
    GetAllRecordsForNameInput,
    UpdateRecordInput,
)
from kluky_mcp.tools.uc3 import _normalize_label
from kluky_mcp.tools.uc3 import register as register_uc3


class _ToolRegistry:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, name: str, annotations: dict[str, object]) -> Any:
        _ = annotations

        def decorator(func: Any) -> Any:
            self.tools[name] = func
            return func

        return decorator


@pytest.fixture()
def real_db_connection() -> Iterator[Any]:
    try:
        conn = get_db_connection()
    except Exception as exc:  # pragma: no cover - depends on runner environment
        pytest.skip(f"Real DB is not available: {exc}")

    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def uc3_tools() -> dict[str, Any]:
    registry = _ToolRegistry()
    register_uc3(registry)  # type: ignore[arg-type]
    return registry.tools


def test_export_all_records_to_csv_desktop_is_registered(
    uc3_tools: dict[str, Any],
) -> None:
    assert "export_all_records_to_csv_desktop" in uc3_tools


@pytest.fixture()
def existing_tool_names(real_db_connection: Any) -> list[str]:
    with real_db_connection.cursor() as cur:
        cur.execute(
            """
            SELECT name
            FROM resources
            WHERE deleted = false
            ORDER BY id
            LIMIT 3
            """
        )
        rows = cur.fetchall()
    return [row[0] for row in rows]


def test_export_all_records_to_csv_desktop_runs_against_real_db(
    real_db_connection: Any,
    uc3_tools: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    existing_tool_names: list[str],
) -> None:
    _ = real_db_connection  # len aby sa test skipol, ak DB nie je dostupna

    monkeypatch.setattr(
        uc3_module,
        "_get_desktop_dir",
        lambda: tmp_path,
    )

    first_name, last_name, subject_name = _make_identity()
    what_i_am_fixing = "retaz"
    raw_text = "Export test - vymena retaze"
    repaired_with = existing_tool_names[:1] if existing_tool_names else []

    _cleanup_identity(real_db_connection, first_name, last_name, subject_name)

    try:
        add_result = uc3_tools["add_record_if_not_exists"](
            AddRecordIfNotExistsInput(
                first_name=first_name,
                last_name=last_name,
                subject_name=subject_name,
                what_i_am_fixing=what_i_am_fixing,
                raw_text=raw_text,
                repaired_with=repaired_with,
            )
        )
        assert add_result == "pridal som"

        result = uc3_tools["export_all_records_to_csv_desktop"](
            ExportAllRecordsToCsvDesktopInput(filename="export_test.csv")
        )

        output_path = Path(result)

        assert output_path.exists()
        assert output_path.name == "export_test.csv"

        content = output_path.read_text(encoding="utf-8-sig")
        lines = content.splitlines()

        assert lines
        assert lines[0] == (
            "record_id,log_id,first_name,last_name,subject_name,"
            "first_mention,last_update,dt,what_i_am_fixing,"
            "work_desc,faults,raw_data,repaired_with"
        )
        assert len(lines) >= 2
        csv_body = "\n".join(lines[1:])
        assert first_name in csv_body
        assert subject_name in csv_body
    finally:
        _cleanup_identity(real_db_connection, first_name, last_name, subject_name)


def _cleanup_identity(
    conn: Any,
    first_name: str,
    last_name: str,
    subject_name: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM users WHERE first_name = %s AND last_name = %s",
            (first_name, last_name),
        )
        user_ids = [row[0] for row in cur.fetchall()]

        cur.execute(
            "SELECT id FROM items WHERE name = %s AND code IS NULL",
            (subject_name,),
        )
        item_ids = [row[0] for row in cur.fetchall()]

        record_ids: list[int] = []
        if user_ids and item_ids:
            cur.execute(
                """
                SELECT id
                FROM repair_records
                WHERE user_id = ANY(%s)
                  AND item_id = ANY(%s)
                """,
                (user_ids, item_ids),
            )
            record_ids = [row[0] for row in cur.fetchall()]

        log_ids: list[int] = []
        if record_ids:
            cur.execute(
                "SELECT id FROM repair_logs WHERE record_id = ANY(%s)",
                (record_ids,),
            )
            log_ids = [row[0] for row in cur.fetchall()]

        if log_ids:
            cur.execute(
                "DELETE FROM repair_log_tools WHERE log_id = ANY(%s)",
                (log_ids,),
            )
            cur.execute(
                "DELETE FROM repair_logs WHERE id = ANY(%s)",
                (log_ids,),
            )

        if record_ids:
            cur.execute(
                "DELETE FROM repair_records WHERE id = ANY(%s)",
                (record_ids,),
            )

        if item_ids:
            cur.execute("DELETE FROM parts WHERE item_id = ANY(%s)", (item_ids,))
            cur.execute("DELETE FROM items WHERE id = ANY(%s)", (item_ids,))

        if user_ids:
            cur.execute("DELETE FROM users WHERE id = ANY(%s)", (user_ids,))

    conn.commit()


def _make_identity() -> tuple[str, str, str]:
    suffix = uuid4().hex[:10]
    first_name = _normalize_label(f"uc3first{suffix}")
    last_name = _normalize_label(f"uc3last{suffix}")
    subject_name = _normalize_label(f"uc3bike{suffix}")
    return first_name, last_name, subject_name


def _fetch_latest_record_row(
    conn: Any,
    first_name: str,
    last_name: str,
    subject_name: str,
) -> tuple[Any, ...] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                rr.id,
                rl.id,
                u.first_name,
                u.last_name,
                i.name,
                p.name,
                rl.work_desc,
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
              AND i.name = %s
            GROUP BY rr.id, rl.id, u.first_name, u.last_name, i.name, p.name,
                     rl.work_desc, rl.raw_data
            ORDER BY rl.id DESC NULLS LAST, rr.id DESC
            LIMIT 1
            """,
            (first_name, last_name, subject_name),
        )
        return cur.fetchone()


def test_kluky_add_record_if_not_exists_contract(
    real_db_connection: Any,
    uc3_tools: dict[str, Any],
    existing_tool_names: list[str],
) -> None:
    """add_record_if_not_exists writes a real record, log, part and tool links."""
    first_name, last_name, subject_name = _make_identity()
    what_i_am_fixing = "retaz"
    raw_text = "Vymena retaze a cistenie pohonu"
    repaired_with = existing_tool_names[:1]

    _cleanup_identity(real_db_connection, first_name, last_name, subject_name)

    try:
        result = uc3_tools["add_record_if_not_exists"](
            AddRecordIfNotExistsInput(
                first_name=first_name,
                last_name=last_name,
                subject_name=subject_name,
                what_i_am_fixing=what_i_am_fixing,
                raw_text=raw_text,
                repaired_with=repaired_with + ["__missing_tool__"],
            )
        )

        assert result == "pridal som"

        row = _fetch_latest_record_row(
            real_db_connection,
            first_name,
            last_name,
            subject_name,
        )
        assert row is not None
        assert row[2] == first_name
        assert row[3] == last_name
        assert row[4] == subject_name
        assert row[5] == what_i_am_fixing
        assert row[6] == raw_text
        assert row[7] == raw_text
        assert row[8] == sorted(repaired_with)
    finally:
        _cleanup_identity(real_db_connection, first_name, last_name, subject_name)


def test_kluky_get_all_records_for_name_contract(
    real_db_connection: Any,
    uc3_tools: dict[str, Any],
    existing_tool_names: list[str],
) -> None:
    """get_all_records_for_name returns the freshly inserted live DB record."""
    first_name, last_name, subject_name = _make_identity()
    what_i_am_fixing = "brzdy"
    raw_text = "Nastavenie prednej brzdy"
    repaired_with = existing_tool_names[:2]

    _cleanup_identity(real_db_connection, first_name, last_name, subject_name)

    try:
        add_result = uc3_tools["add_record_if_not_exists"](
            AddRecordIfNotExistsInput(
                first_name=first_name,
                last_name=last_name,
                subject_name=subject_name,
                what_i_am_fixing=what_i_am_fixing,
                raw_text=raw_text,
                repaired_with=repaired_with,
            )
        )
        assert add_result == "pridal som"

        records = uc3_tools["get_all_records_for_name"](
            GetAllRecordsForNameInput(first_name=first_name, last_name=last_name)
        )

        matching = [
            record for record in records if record["subject_name"] == subject_name
        ]
        assert matching

        latest = matching[0]
        assert latest["first_name"] == first_name
        assert latest["last_name"] == last_name
        assert latest["subject_name"] == subject_name
        assert latest["what_i_am_fixing"] == what_i_am_fixing
        assert latest["work_desc"] == raw_text
        assert latest["raw_data"] == raw_text
        assert latest["repaired_with"] == sorted(repaired_with)
        assert latest["record_id"]
        assert latest["log_id"]
        assert latest["first_mention"]
        assert latest["last_update"]
        assert latest["dt"]
    finally:
        _cleanup_identity(real_db_connection, first_name, last_name, subject_name)


def test_kluky_update_record_contract(
    real_db_connection: Any,
    uc3_tools: dict[str, Any],
    existing_tool_names: list[str],
) -> None:
    """update_record appends text, changes the part and keeps tool links in DB."""
    first_name, last_name, subject_name = _make_identity()
    initial_fix = "retaz"
    initial_text = "Vyčistenie pohonu"
    update_fix = "kazeta"
    update_text = "Doplnena vymena kazety"
    initial_tools = existing_tool_names[:1]
    update_tools = existing_tool_names[1:2] or existing_tool_names[:1]

    _cleanup_identity(real_db_connection, first_name, last_name, subject_name)

    try:
        add_result = uc3_tools["add_record_if_not_exists"](
            AddRecordIfNotExistsInput(
                first_name=first_name,
                last_name=last_name,
                subject_name=subject_name,
                what_i_am_fixing=initial_fix,
                raw_text=initial_text,
                repaired_with=initial_tools,
            )
        )
        assert add_result == "pridal som"

        inserted = _fetch_latest_record_row(
            real_db_connection,
            first_name,
            last_name,
            subject_name,
        )
        assert inserted is not None

        record_id = inserted[0]
        log_id = inserted[1]

        result = uc3_tools["update_record"](
            UpdateRecordInput(
                record_id=str(record_id),
                log_id=str(log_id),
                what_i_am_fixing=update_fix,
                raw_text=update_text,
                repaired_with=update_tools,
            )
        )

        assert result == "update sa podaril"

        updated = _fetch_latest_record_row(
            real_db_connection,
            first_name,
            last_name,
            subject_name,
        )
        assert updated is not None
        assert updated[0] == record_id
        assert updated[1] == log_id
        assert updated[5] == update_fix
        assert updated[6] == f"{initial_text}\n{update_text}"
        assert updated[7] == f"{initial_text}\n{update_text}"
        assert updated[8] == sorted({*initial_tools, *update_tools})
    finally:
        _cleanup_identity(real_db_connection, first_name, last_name, subject_name)
