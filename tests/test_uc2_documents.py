"""UC2 tests for document catalog and detail retrieval behavior."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, cast

from pydantic import ValidationError

from kluky_mcp.models import GetDocumentInfoInput
from kluky_mcp.tools.uc02_utils.pageIndexRetrieval import fetch_document_text
from kluky_mcp.tools.uc2 import _catalog_candidates, _manuals_catalog, _topics_by_manual


def _test_banner(name: str) -> None:
    print(f"[UC02 TEST] {name}")


def test_catalog_candidates_prioritize_matching_sections() -> None:
    _test_banner("catalog candidates prioritize matching sections")

    units_catalog = [
        {
            "doc_id": "manual-a::1",
            "manual_name": "manual_Bicykle_SK.pdf",
            "title": "NASTAVENIE PREHADZOVACKY",
            "summary": "Postup nastavenia zadnej prehadzovacky krok za krokom.",
            "unit_no": 24,
            "start_page": 16,
            "end_page": 16,
            "updated_at": "2026-03-07T10:00:00",
        },
        {
            "doc_id": "manual-a::2",
            "manual_name": "manual_Bicykle_SK.pdf",
            "title": "CISTENIE Ramu",
            "summary": "Udrzba ramu a laku.",
            "unit_no": 4,
            "start_page": 6,
            "end_page": 6,
            "updated_at": "2026-03-07T10:00:00",
        },
        {
            "doc_id": "manual-b::1",
            "manual_name": "manual_MTB.pdf",
            "title": "Brzdy",
            "summary": "Nastavenie brzdovej paky.",
            "unit_no": 3,
            "start_page": 5,
            "end_page": 6,
            "updated_at": "2026-03-06T09:00:00",
        },
    ]

    results = _catalog_candidates(
        units_catalog,
        queries=["ako nastavit prehadzovacku"],
        manual_doc_id=None,
        top_k=3,
    )

    assert len(results) == 3
    assert results[0]["title"] == "NASTAVENIE PREHADZOVACKY"
    assert results[0]["manual"] == "manual_Bicykle_SK.pdf"
    assert results[0]["selection_mode"] == "catalog_only"


def test_manuals_catalog_returns_all_manuals_with_section_counts() -> None:
    _test_banner("manuals catalog returns all manuals with counts")

    units_catalog = [
        {"manual_name": "manual_A.pdf"},
        {"manual_name": "manual_B.pdf"},
        {"manual_name": "manual_A.pdf"},
    ]

    catalog = _manuals_catalog(units_catalog)

    assert catalog == [
        {"manual": "manual_A.pdf", "sections_count": 2},
        {"manual": "manual_B.pdf", "sections_count": 1},
    ]


def test_topics_by_manual_groups_unique_titles() -> None:
    _test_banner("topics by manual groups unique section titles")

    units_catalog = [
        {"doc_id": "m1::1", "manual_name": "manual_A.pdf", "title": "Brzdy"},
        {"doc_id": "m1::2", "manual_name": "manual_A.pdf", "title": "Brzdy"},
        {"doc_id": "m1::3", "manual_name": "manual_A.pdf", "title": "Retaz"},
    ]

    topics = _topics_by_manual(units_catalog, manual_doc_id=None)

    assert topics == [{"manual": "manual_A.pdf", "topics": ["Brzdy", "Retaz"]}]


def test_get_document_info_input_requires_doc_id_or_manual_name() -> None:
    _test_banner("document info input validates identifiers")

    try:
        GetDocumentInfoInput()
        assert False, (
            "Expected ValidationError when doc_id and manual_name are missing."
        )
    except ValidationError:
        pass

    model = GetDocumentInfoInput(manual_name="manual_Bicykle_SK.pdf", unit_no=24)
    assert model.manual_name == "manual_Bicykle_SK.pdf"
    assert model.doc_id is None
    assert model.unit_no == 24


@dataclass
class _ScriptStep:
    fetchone: tuple[Any, ...] | None = None
    fetchall: list[tuple[Any, ...]] | None = None


class _ScriptedCursor:
    def __init__(self, step: _ScriptStep):
        self._step = step

    def __enter__(self) -> "_ScriptedCursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
        return None

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._step.fetchone

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._step.fetchall or []


class _ScriptedConnection:
    def __init__(self, steps: list[_ScriptStep]):
        self._steps: Iterator[_ScriptStep] = iter(steps)

    def cursor(self) -> _ScriptedCursor:
        return _ScriptedCursor(next(self._steps))


def test_fetch_document_text_can_resolve_by_manual_name_and_unit() -> None:
    _test_banner("fetch_document_text resolves manual_name + unit_no")

    conn = _ScriptedConnection(
        [
            _ScriptStep(fetchone=("manual-doc-1",)),
            _ScriptStep(
                fetchone=(
                    "manual-doc-1",
                    "manual_Bicykle_SK.pdf",
                    "Manual Bicykle",
                    "Zakladny manual",
                    "/tmp/manual_Bicykle_SK.pdf",
                    "pdf",
                )
            ),
            _ScriptStep(
                fetchall=[
                    (
                        "section",
                        24,
                        16,
                        16,
                        "Nastavenie prehadzovacky: dorazy, lanko a doladenie.",
                    )
                ]
            ),
        ]
    )

    payload = fetch_document_text(
        cast(Any, conn),
        manual_name="manual_Bicykle_SK.pdf",
        unit_no=24,
    )

    assert payload["doc_id"] == "manual-doc-1"
    assert payload["manual_name"] == "manual_Bicykle_SK.pdf"
    assert payload["unit_no"] == 24
    assert payload["unit_count"] == 1
    assert "unit_no=24" in payload["text"]
