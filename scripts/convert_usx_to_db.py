#!/usr/bin/env python3
"""Convert a DBL/USX bundle into a StudyBible SQLCipher database.

The existing XML converter handles one flattened XML file per translation.
DBL bundles are different: metadata, license, styles, versification, and one
USX file per book. This converter keeps the app-compatible tables intact and
adds richer metadata tables that the app can start using later.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import sqlcipher3 as sqlite3

from convert_to_db import _ENGLISH_BOOK_NAMES, get_encryption_key, load_book_names_lookup


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

BOOK_CODES: list[tuple[str, int, str]] = [
    ("GEN", 1, "OT"),
    ("EXO", 2, "OT"),
    ("LEV", 3, "OT"),
    ("NUM", 4, "OT"),
    ("DEU", 5, "OT"),
    ("JOS", 6, "OT"),
    ("JDG", 7, "OT"),
    ("RUT", 8, "OT"),
    ("1SA", 9, "OT"),
    ("2SA", 10, "OT"),
    ("1KI", 11, "OT"),
    ("2KI", 12, "OT"),
    ("1CH", 13, "OT"),
    ("2CH", 14, "OT"),
    ("EZR", 15, "OT"),
    ("NEH", 16, "OT"),
    ("EST", 17, "OT"),
    ("JOB", 18, "OT"),
    ("PSA", 19, "OT"),
    ("PRO", 20, "OT"),
    ("ECC", 21, "OT"),
    ("SNG", 22, "OT"),
    ("ISA", 23, "OT"),
    ("JER", 24, "OT"),
    ("LAM", 25, "OT"),
    ("EZK", 26, "OT"),
    ("DAN", 27, "OT"),
    ("HOS", 28, "OT"),
    ("JOL", 29, "OT"),
    ("AMO", 30, "OT"),
    ("OBA", 31, "OT"),
    ("JON", 32, "OT"),
    ("MIC", 33, "OT"),
    ("NAM", 34, "OT"),
    ("HAB", 35, "OT"),
    ("ZEP", 36, "OT"),
    ("HAG", 37, "OT"),
    ("ZEC", 38, "OT"),
    ("MAL", 39, "OT"),
    ("MAT", 40, "NT"),
    ("MRK", 41, "NT"),
    ("LUK", 42, "NT"),
    ("JHN", 43, "NT"),
    ("ACT", 44, "NT"),
    ("ROM", 45, "NT"),
    ("1CO", 46, "NT"),
    ("2CO", 47, "NT"),
    ("GAL", 48, "NT"),
    ("EPH", 49, "NT"),
    ("PHP", 50, "NT"),
    ("COL", 51, "NT"),
    ("1TH", 52, "NT"),
    ("2TH", 53, "NT"),
    ("1TI", 54, "NT"),
    ("2TI", 55, "NT"),
    ("TIT", 56, "NT"),
    ("PHM", 57, "NT"),
    ("HEB", 58, "NT"),
    ("JAS", 59, "NT"),
    ("1PE", 60, "NT"),
    ("2PE", 61, "NT"),
    ("1JN", 62, "NT"),
    ("2JN", 63, "NT"),
    ("3JN", 64, "NT"),
    ("JUD", 65, "NT"),
    ("REV", 66, "NT"),
]

BOOK_BY_CODE = {code: (book_id, testament) for code, book_id, testament in BOOK_CODES}


@dataclass
class WordToken:
    book_id: int
    chapter: int
    verse: int
    word_index: int
    text: str
    strong: str | None
    lemma: str | None
    morph: str | None


@dataclass
class VerseNote:
    book_id: int
    chapter: int
    verse: int
    note_index: int
    caller: str | None
    style: str | None
    text: str


@dataclass
class ParsedBook:
    code: str
    book_id: int
    testament: str
    titles: dict[str, str]
    chapter_count: int
    verses: list[tuple[int, int, str]] = field(default_factory=list)
    notes: list[VerseNote] = field(default_factory=list)
    words: list[WordToken] = field(default_factory=list)


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = value.replace("“ ", "“").replace(" ‘", " ‘")
    return value.strip()


def first_text(root: ET.Element, path: str) -> str | None:
    element = root.find(path)
    if element is None:
        return None
    text = clean_text("".join(element.itertext()))
    return text or None


def xml_to_dict(element: ET.Element) -> dict:
    children = list(element)
    data: dict[str, object] = {"attributes": dict(element.attrib)} if element.attrib else {}
    text = clean_text(element.text or "")
    if text:
        data["text"] = text
    for child in children:
        child_value = xml_to_dict(child)
        existing = data.get(child.tag)
        if existing is None:
            data[child.tag] = child_value
        elif isinstance(existing, list):
            existing.append(child_value)
        else:
            data[child.tag] = [existing, child_value]
    return data


def parse_dbl_metadata(bundle_dir: Path) -> tuple[dict[str, str | None], list[tuple[str, str]]]:
    metadata_root = ET.parse(bundle_dir / "metadata.xml").getroot()
    license_path = bundle_dir / "license.xml"
    license_root = ET.parse(license_path).getroot() if license_path.exists() else None

    meta = {
        "id": metadata_root.attrib.get("id"),
        "revision": metadata_root.attrib.get("revision"),
        "name": first_text(metadata_root, "./identification/name"),
        "name_local": first_text(metadata_root, "./identification/nameLocal"),
        "description": first_text(metadata_root, "./identification/description"),
        "abbreviation": first_text(metadata_root, "./identification/abbreviation"),
        "abbreviation_local": first_text(metadata_root, "./identification/abbreviationLocal"),
        "scope": first_text(metadata_root, "./identification/scope"),
        "language_iso3": first_text(metadata_root, "./language/iso"),
        "language_name": first_text(metadata_root, "./language/name"),
        "language_local": first_text(metadata_root, "./language/nameLocal"),
        "script": first_text(metadata_root, "./language/script"),
        "script_code": first_text(metadata_root, "./language/scriptCode"),
        "script_direction": first_text(metadata_root, "./language/scriptDirection"),
        "ldml": first_text(metadata_root, "./language/ldml"),
        "rights_holder": first_text(metadata_root, "./agencies/rightsHolder/name"),
        "rights_holder_url": first_text(metadata_root, "./agencies/rightsHolder/url"),
        "rights_admin": first_text(metadata_root, "./agencies/rightsAdmin/name"),
        "usx_version": first_text(metadata_root, "./format/usxVersion"),
        "versed_paragraphs": first_text(metadata_root, "./format/versedParagraphs"),
    }

    raw_rows = [
        ("metadata_xml", json.dumps(xml_to_dict(metadata_root), ensure_ascii=False, sort_keys=True))
    ]
    if license_root is not None:
        raw_rows.append(
            ("license_xml", json.dumps(xml_to_dict(license_root), ensure_ascii=False, sort_keys=True))
        )
        for path in (
            "./publicationRights/allowIntroductions",
            "./publicationRights/allowFootnotes",
            "./publicationRights/allowCrossReferences",
            "./publicationRights/allowExtendedNotes",
        ):
            key = path.rsplit("/", 1)[-1]
            meta[key] = first_text(license_root, path)

    return meta, raw_rows


def parse_verse_number(value: str) -> int:
    match = re.match(r"\d+", value)
    if not match:
        raise ValueError(f"Unsupported verse number: {value}")
    return int(match.group(0))


def parse_usx_book(usx_path: Path) -> ParsedBook:
    root = ET.parse(usx_path).getroot()
    book_element = root.find("book")
    code = (book_element.attrib.get("code") if book_element is not None else usx_path.stem).upper()
    if code not in BOOK_BY_CODE:
        raise ValueError(f"{usx_path.name}: unsupported book code {code}")

    book_id, testament = BOOK_BY_CODE[code]
    titles: dict[str, str] = {}
    chapter = 0
    verse: int | None = None
    buffer: list[str] = []
    verses: list[tuple[int, int, str]] = []
    state = {"book_id": book_id, "notes": [], "words": [], "word_index": 0}

    def flush() -> None:
        nonlocal buffer, verse
        if verse is None:
            buffer = []
            return
        text = clean_text("".join(buffer))
        verses.append((chapter, verse, text))
        buffer = []

    def current_ref() -> tuple[int, int] | None:
        if chapter and verse is not None:
            return chapter, verse
        return None

    def append_text(value: str | None) -> None:
        if value and current_ref() is not None:
            buffer.append(value)

    def process(element: ET.Element) -> None:
        nonlocal chapter, verse

        if element.tag == "chapter" and "number" in element.attrib:
            flush()
            chapter = int(element.attrib["number"])
            verse = None
            return
        if element.tag == "chapter" and "eid" in element.attrib:
            flush()
            verse = None
            return
        if element.tag == "verse" and "number" in element.attrib:
            flush()
            verse = parse_verse_number(element.attrib["number"])
            state["word_index"] = 0
            return
        if element.tag == "verse" and "eid" in element.attrib:
            flush()
            verse = None
            return
        if element.tag == "note":
            ref = current_ref()
            if ref is not None or chapter:
                note_text = clean_text("".join(element.itertext()))
                if note_text:
                    note_chapter, note_verse = ref or (chapter, 0)
                    state["notes"].append(
                        VerseNote(
                            book_id=book_id,
                            chapter=note_chapter,
                            verse=note_verse,
                            note_index=len(state["notes"]) + 1,
                            caller=element.attrib.get("caller"),
                            style=element.attrib.get("style"),
                            text=note_text,
                        )
                    )
            return

        if element.tag == "char" and element.attrib.get("style") == "w":
            ref = current_ref()
            word_text = clean_text("".join(element.itertext()))
            if ref is not None and word_text:
                word_chapter, word_verse = ref
                state["word_index"] += 1
                state["words"].append(
                    WordToken(
                        book_id=book_id,
                        chapter=word_chapter,
                        verse=word_verse,
                        word_index=state["word_index"],
                        text=word_text,
                        strong=element.attrib.get("strong"),
                        lemma=element.attrib.get("lemma"),
                        morph=element.attrib.get("morph"),
                    )
                )

        append_text(element.text)
        for child in element:
            process(child)
            append_text(child.tail)

    for element in root:
        if element.tag == "para":
            style = element.attrib.get("style")
            if style in {"h", "toc1", "toc2", "toc3", "mt1", "mt2", "mt3"}:
                title = clean_text("".join(element.itertext()))
                if title:
                    titles[style] = title
        process(element)

    flush()
    return ParsedBook(
        code=code,
        book_id=book_id,
        testament=testament,
        titles=titles,
        chapter_count=chapter,
        verses=verses,
        notes=state["notes"],
        words=state["words"],
    )


def connect_database(db_path: Path, key_hex: str | None) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if key_hex:
        cursor.execute(f"PRAGMA key = \"x'{key_hex}'\"")
        cursor.execute("PRAGMA cipher_page_size = 4096")
        cursor.execute("PRAGMA kdf_iter = 256000")
        cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
        cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
    return conn


def create_schema(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE translations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            language TEXT NOT NULL,
            language_name TEXT,
            description TEXT,
            download_url TEXT,
            legal_notice TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE books (
            translation_id TEXT NOT NULL,
            id INTEGER NOT NULL,
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            chapter_count INTEGER NOT NULL,
            testament TEXT NOT NULL,
            PRIMARY KEY (translation_id, id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE verses (
            translation_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY (translation_id, book_id, chapter, verse)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE book_names (
            book_id INTEGER NOT NULL,
            native TEXT NOT NULL,
            english TEXT NOT NULL,
            PRIMARY KEY (book_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE translation_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE book_metadata (
            book_id INTEGER PRIMARY KEY,
            code TEXT NOT NULL,
            header TEXT,
            toc1 TEXT,
            toc2 TEXT,
            toc3 TEXT,
            title TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE verse_notes (
            translation_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            note_index INTEGER NOT NULL,
            caller TEXT,
            style TEXT,
            text TEXT NOT NULL,
            PRIMARY KEY (translation_id, book_id, chapter, verse, note_index)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE verse_words (
            translation_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            word_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            strong TEXT,
            lemma TEXT,
            morph TEXT,
            PRIMARY KEY (translation_id, book_id, chapter, verse, word_index)
        )
        """
    )
    cursor.execute(
        "CREATE INDEX idx_verse_notes_ref ON verse_notes (translation_id, book_id, chapter, verse)"
    )
    cursor.execute(
        "CREATE INDEX idx_verse_words_ref ON verse_words (translation_id, book_id, chapter, verse)"
    )
    cursor.execute("CREATE INDEX idx_verse_words_strong ON verse_words (strong)")


def convert_usx_bundle(
    bundle_dir: Path,
    db_path: Path,
    *,
    translation_id: str | None,
    plain: bool,
) -> dict[str, int | str]:
    bundle_dir = bundle_dir.resolve()
    usx_dir = bundle_dir / "release" / "USX_4"
    if not usx_dir.exists():
        raise FileNotFoundError(f"USX directory not found: {usx_dir}")

    metadata, raw_metadata = parse_dbl_metadata(bundle_dir)
    translation_id = translation_id or re.sub(
        r"[^a-z0-9]+", "-", (metadata.get("abbreviation") or bundle_dir.name).lower()
    ).strip("-")

    key_hex = None
    if not plain:
        key_hex = base64.b64decode(get_encryption_key()).hex()

    books = [parse_usx_book(path) for path in sorted(usx_dir.glob("*.usx"))]
    books.sort(key=lambda book: book.book_id)

    conn = connect_database(db_path, key_hex)
    cursor = conn.cursor()
    create_schema(cursor)

    language = metadata.get("ldml") or metadata.get("language_iso3") or "und"
    cursor.execute(
        """
        INSERT INTO translations
            (id, name, abbreviation, language, language_name, description, download_url, legal_notice)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            translation_id,
            metadata.get("name") or translation_id,
            metadata.get("abbreviation_local") or metadata.get("abbreviation") or translation_id,
            language,
            metadata.get("language_name"),
            metadata.get("description"),
            None,
            metadata.get("rights_holder"),
        ),
    )

    cursor.executemany(
        "INSERT INTO translation_metadata (key, value) VALUES (?, ?)",
        [(key, value) for key, value in metadata.items() if value is not None] + raw_metadata,
    )

    book_name_lookup = load_book_names_lookup(PROJECT_DIR).get(str(language), {})
    for book in books:
        fallback_name = _ENGLISH_BOOK_NAMES.get(str(book.book_id), book.code)
        name = book.titles.get("toc2") or book.titles.get("h") or fallback_name
        abbreviation = book.titles.get("toc3") or book.code
        cursor.execute(
            """
            INSERT INTO books
                (translation_id, id, name, abbreviation, chapter_count, testament)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (translation_id, book.book_id, name, abbreviation, book.chapter_count, book.testament),
        )
        cursor.execute(
            "INSERT INTO book_names (book_id, native, english) VALUES (?, ?, ?)",
            (book.book_id, book_name_lookup.get(str(book.book_id), name), fallback_name),
        )
        cursor.execute(
            """
            INSERT INTO book_metadata (book_id, code, header, toc1, toc2, toc3, title)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                book.book_id,
                book.code,
                book.titles.get("h"),
                book.titles.get("toc1"),
                book.titles.get("toc2"),
                book.titles.get("toc3"),
                book.titles.get("mt1"),
            ),
        )

    cursor.executemany(
        """
        INSERT INTO verses (translation_id, book_id, chapter, verse, text)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (translation_id, book.book_id, chapter, verse, text)
            for book in books
            for chapter, verse, text in book.verses
        ],
    )
    cursor.executemany(
        """
        INSERT INTO verse_notes
            (translation_id, book_id, chapter, verse, note_index, caller, style, text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                translation_id,
                note.book_id,
                note.chapter,
                note.verse,
                note.note_index,
                note.caller,
                note.style,
                note.text,
            )
            for book in books
            for note in book.notes
        ],
    )
    cursor.executemany(
        """
        INSERT INTO verse_words
            (translation_id, book_id, chapter, verse, word_index, text, strong, lemma, morph)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                translation_id,
                word.book_id,
                word.chapter,
                word.verse,
                word.word_index,
                word.text,
                word.strong,
                word.lemma,
                word.morph,
            )
            for book in books
            for word in book.words
        ],
    )

    conn.commit()
    conn.close()

    return {
        "translation_id": translation_id,
        "db_path": str(db_path),
        "books": len(books),
        "chapters": sum(book.chapter_count for book in books),
        "verses": sum(len(book.verses) for book in books),
        "notes": sum(len(book.notes) for book in books),
        "word_tokens": sum(len(book.words) for book in books),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a DBL/USX Bible bundle to SQLCipher DB.")
    parser.add_argument(
        "bundle_dir",
        nargs="?",
        default=PROJECT_DIR / "usx_test_files" / "text-04da588535d2f823-240018",
        type=Path,
        help="DBL bundle directory containing metadata.xml and release/USX_4.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output DB path. Defaults to database/translations/<translation-id>.db.",
    )
    parser.add_argument("--id", dest="translation_id", help="Override generated translation id.")
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Create a plain SQLite DB for inspection instead of encrypted SQLCipher.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata, _ = parse_dbl_metadata(args.bundle_dir)
    translation_id = args.translation_id or re.sub(
        r"[^a-z0-9]+", "-", (metadata.get("abbreviation") or args.bundle_dir.name).lower()
    ).strip("-")
    output = args.output or PROJECT_DIR / "database" / "translations" / f"{translation_id}.db"
    output.parent.mkdir(parents=True, exist_ok=True)

    result = convert_usx_bundle(
        args.bundle_dir,
        output,
        translation_id=translation_id,
        plain=args.plain,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
