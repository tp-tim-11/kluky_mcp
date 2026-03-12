from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

from markitdown import MarkItDown

# ----------------------------
# 1) SQL pre Supabase/Postgres
# ----------------------------

SUPABASE_SQL_CREATE = """
    create table if not exists doc_units (
    id bigserial primary key,
    doc_id text not null,
    manual_name text not null,
    source_path text not null,
    source_type text not null,         -- pdf/docx/html/txt/...
    unit_type text not null,           -- page/section/chunk
    unit_no int,                       -- page number alebo poradie sekcie/chunku
    start_page int,
    end_page int,
    title text,                        -- názov dokumentu alebo sekcie
    heading_path text,                 -- napr "Servis > Brzdy > Odvzdušnenie"
    summary text,                      -- stručné zhrnutie unitu
    text text not null,
    created_at timestamptz default now(),

    -- fulltext (simple = stabilné pre SK/CZ bez stemming komplikácií)
    search_vector tsvector generated always as (
        to_tsvector(
        'simple',
        coalesce(title,'') || ' ' || coalesce(summary,'') || ' ' || coalesce(text,'')
        )
    ) stored
    );

    create index if not exists doc_units_search_idx
    on doc_units using gin (search_vector);

    create index if not exists doc_units_doc_idx
    on doc_units (doc_id);

    create unique index if not exists doc_units_unique_unit_idx
    on doc_units (doc_id, unit_type, unit_no);

    alter table if exists doc_units
    add column if not exists manual_name text;

    update doc_units
    set manual_name = regexp_replace(source_path, '^.*[\\/]', '')
    where manual_name is null or manual_name = '';

    create index if not exists doc_units_manual_name_idx
    on doc_units (manual_name);
""".strip()

# --------------------------------
# 2) Pomocné util funkcie (text)
# --------------------------------


def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def stable_doc_id_from_source_path(path: str) -> str:
    """
    Stabilné doc_id podľa source_path (možnosť 1 - verzovanie pod jedným ID).
    Pri zmene obsahu rovnakého súboru zostáva doc_id rovnaké a reindex prepíše obsah.
    """
    normalized = os.path.normcase(os.path.normpath(os.path.abspath(path)))
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def stable_doc_id_from_doc_key(doc_key: str) -> str:
    """
    Stabilné doc_id podľa externého kľúča dokumentu.
    Vhodné keď sa mení názov/cesta súboru, ale ide stále o ten istý manuál.
    """
    normalized = _norm_space(doc_key).lower()
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def convert_to_markdown(path: str) -> str:
    """Convert supported file types to markdown/text payload."""
    mid = MarkItDown()
    suffix = Path(path).suffix.lower()
    text_like_suffixes = {
        ".txt",
        ".md",
        ".markdown",
        ".csv",
        ".tsv",
        ".json",
        ".xml",
        ".html",
        ".htm",
        ".log",
    }
    try:
        result = mid.convert(path)
        text = result.text_content or ""
        if suffix == ".pdf" and len(text.strip()) < 20:
            raise RuntimeError(
                f"'{path}' vyzera ako naskenovane PDF (bez textovej vrstvy)."
            )
        return text
    except Exception as exc:
        if suffix not in text_like_suffixes:
            raise RuntimeError(
                f"Konverzia zlyhala pre '{path}' a fallback citanie nie je bezpecne pre binarny format '{suffix or 'unknown'}': {exc}"
            ) from exc
        try:
            with open(path, encoding="utf-8", errors="ignore") as file_obj:
                return file_obj.read()
        except Exception as fallback_exc:
            raise RuntimeError(
                f"Konverzia alebo fallback citanie zlyhalo pre '{path}': {exc}"
            ) from fallback_exc


# ----------------------------
# Store: zapis do Postgres
# ----------------------------


@dataclass
class DocUnit:
    unit_type: str
    unit_no: int | None
    start_page: int | None
    end_page: int | None
    title: str | None
    heading_path: str | None
    summary: str | None
    text: str


class PageIndexStore:
    """
    pg_conn: psycopg2 connection alebo iný DB-API 2.0 connection (cursor, execute, executemany, commit).
    """

    def __init__(self, pg_conn: object) -> None:
        self.pg = pg_conn

    def reindex_doc(
        self,
        doc_id: str,
        manual_name: str,
        source_path: str,
        source_type: str,
        units: list[DocUnit],
    ) -> None:
        """
        Idempotentný reindex: zmaže existujúce units pre doc a vloží nové.
        """
        with self.pg.cursor() as cur:
            cur.execute(
                "delete from doc_units where doc_id=%s",
                (doc_id,),
            )

            rows = [
                (
                    doc_id,
                    manual_name,
                    source_path,
                    source_type,
                    u.unit_type,
                    u.unit_no,
                    u.start_page,
                    u.end_page,
                    u.title,
                    u.heading_path,
                    u.summary,
                    u.text,
                )
                for u in units
            ]

            cur.executemany(
                """
                insert into doc_units
                  (doc_id, manual_name, source_path, source_type, unit_type, unit_no, start_page, end_page, title, heading_path, summary, text)
                values
                  (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                rows,
            )
        self.pg.commit()
