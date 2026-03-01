import os
import json
import re
import sqlcipher3 as sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import base64


# ---------------------------------------------------------------------------
# Language helpers (mirrors logic in generate_index.py)
# ---------------------------------------------------------------------------

# Mapping from normalised language name -> ISO 639-1 code
_LANGUAGE_ISO_MAP = {
    'English': 'en', 'Chinese': 'zh', 'Arabic': 'ar', 'Spanish': 'es',
    'French': 'fr', 'German': 'de', 'Portuguese': 'pt', 'Russian': 'ru',
    'Korean': 'ko', 'Japanese': 'ja', 'Hindi': 'hi', 'Tamil': 'ta',
    'Telugu': 'te', 'Bengali': 'bn', 'Gujarati': 'gu', 'Marathi': 'mr',
    'Malayalam': 'ml', 'Kannada': 'kn', 'Punjabi': 'pa', 'Urdu': 'ur',
    'Persian': 'fa', 'Turkish': 'tr', 'Hebrew': 'he', 'Greek': 'el',
    'Latin': 'la', 'Italian': 'it', 'Dutch': 'nl', 'Swedish': 'sv',
    'Norwegian': 'no', 'Danish': 'da', 'Finnish': 'fi', 'Polish': 'pl',
    'Czech': 'cs', 'Slovak': 'sk', 'Hungarian': 'hu', 'Romanian': 'ro',
    'Bulgarian': 'bg', 'Serbian': 'sr', 'Croatian': 'hr', 'Slovenian': 'sl',
    'Albanian': 'sq', 'Estonian': 'et', 'Latvian': 'lv', 'Lithuanian': 'lt',
    'Ukrainian': 'uk', 'Belarusian': 'be', 'Indonesian': 'id',
    'Vietnamese': 'vi', 'Thai': 'th', 'Swahili': 'sw', 'Amharic': 'am',
    'Afrikaans': 'af', 'Malagasy': 'mg', 'Maori': 'mi', 'Welsh': 'cy',
    'Irish': 'ga', 'Gaelic': 'gd', 'Icelandic': 'is', 'Catalan': 'ca',
    'Basque': 'eu', 'Esperanto': 'eo', 'Armenian': 'hy', 'Georgian': 'ka',
    'Mongolian': 'mn', 'Khmer': 'km', 'Lao': 'lo', 'Tibetan': 'bo',
    'Sinhalese': 'si', 'Sinhala': 'si', 'Nepali': 'ne', 'Assamese': 'as',
    'Odia': 'or', 'Maithili': 'mai', 'Azerbaijani': 'az', 'Kazakh': 'kk',
    'Kyrgyz': 'ky', 'Uzbek': 'uz', 'Turkish': 'tr', 'Tajik': 'tg',
    'Turkmen': 'tk',
}

_BASE_LANGUAGES = list(_LANGUAGE_ISO_MAP.keys())


def _normalize_language_name(base_name: str) -> str:
    """Return a normalised language name from a raw filename stem fragment."""
    if base_name.startswith('Chin') and not base_name.startswith('Chinese'):
        return 'Chin'
    if base_name.startswith('Original'):
        if 'Greek' in base_name:
            return 'Greek'
        if 'Hebrew' in base_name:
            return 'Hebrew'
    for lang in _BASE_LANGUAGES:
        if base_name.startswith(lang):
            return lang
    return base_name


def iso_from_filename(filename: str) -> str | None:
    """Derive the ISO 639-1 code from a Bible XML filename, or None."""
    base = Path(filename).stem  # e.g. "TamilBible"
    base = base.replace('Bible', '')
    base = re.sub(r'\d{4}', '', base)        # strip years
    base = re.sub(r'[A-Z]{2,5}$', '', base)  # strip trailing version codes
    lang = _normalize_language_name(base)
    return _LANGUAGE_ISO_MAP.get(lang)


# ---------------------------------------------------------------------------
# Book-names JSON loader
# ---------------------------------------------------------------------------

def load_book_names_lookup(project_dir: Path) -> dict:
    """
    Load bible-book-names.json and return a lookup structure::

        {
            'en': {'1': 'Genesis', '2': 'Exodus', ...},
            'ta': {'1': 'ஆதியாகமம்', ...},
            ...
        }
    """
    book_names_path = project_dir / 'bible-book-names.json'
    if not book_names_path.exists():
        print(f"Warning: {book_names_path} not found. Book names will use English fallback.")
        return {}

    with open(book_names_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    lookup: dict[str, dict[str, str]] = {}
    for iso_code, lang_data in data.get('languages', {}).items():
        books = lang_data.get('books', {})
        # Normalise keys to strings, values to plain strings
        # (some entries in older versions stored dicts with 'native_name' sub-key)
        normalised: dict[str, str] = {}
        for k, v in books.items():
            if isinstance(v, dict):
                normalised[str(k)] = v.get('native_name', '')
            else:
                normalised[str(k)] = str(v)
        lookup[iso_code] = normalised

    return lookup


# English fallback names for all 66 books
_ENGLISH_BOOK_NAMES: dict[str, str] = {
    '1': 'Genesis', '2': 'Exodus', '3': 'Leviticus', '4': 'Numbers',
    '5': 'Deuteronomy', '6': 'Joshua', '7': 'Judges', '8': 'Ruth',
    '9': '1 Samuel', '10': '2 Samuel', '11': '1 Kings', '12': '2 Kings',
    '13': '1 Chronicles', '14': '2 Chronicles', '15': 'Ezra',
    '16': 'Nehemiah', '17': 'Esther', '18': 'Job', '19': 'Psalms',
    '20': 'Proverbs', '21': 'Ecclesiastes', '22': 'Song of Solomon',
    '23': 'Isaiah', '24': 'Jeremiah', '25': 'Lamentations', '26': 'Ezekiel',
    '27': 'Daniel', '28': 'Hosea', '29': 'Joel', '30': 'Amos',
    '31': 'Obadiah', '32': 'Jonah', '33': 'Micah', '34': 'Nahum',
    '35': 'Habakkuk', '36': 'Zephaniah', '37': 'Haggai', '38': 'Zechariah',
    '39': 'Malachi', '40': 'Matthew', '41': 'Mark', '42': 'Luke',
    '43': 'John', '44': 'Acts', '45': 'Romans', '46': '1 Corinthians',
    '47': '2 Corinthians', '48': 'Galatians', '49': 'Ephesians',
    '50': 'Philippians', '51': 'Colossians', '52': '1 Thessalonians',
    '53': '2 Thessalonians', '54': '1 Timothy', '55': '2 Timothy',
    '56': 'Titus', '57': 'Philemon', '58': 'Hebrews', '59': 'James',
    '60': '1 Peter', '61': '2 Peter', '62': '1 John', '63': '2 John',
    '64': '3 John', '65': 'Jude', '66': 'Revelation',
}


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def get_encryption_key():
    """Load the encryption key from .env file."""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    env_path = project_dir / ".env"
    if not env_path.exists():
        raise FileNotFoundError(".env file not found. Ensure ENCRYPTION_KEY is set.")

    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("ENCRYPTION_KEY="):
                return line.strip().split("ENCRYPTION_KEY=")[1]

    raise ValueError("ENCRYPTION_KEY not found in .env file.")


def convert_xml_to_db(xml_path: Path, db_path: Path, encryption_key: str,
                      book_names_lookup: dict) -> int:
    """Convert a single Bible XML file to an encrypted SQLite DB.

    Args:
        xml_path: Source XML file.
        db_path: Destination .db file.
        encryption_key: Hex-encoded SQLCipher key.
        book_names_lookup: Mapping of iso_code -> {book_num_str -> native_name}.

    Returns:
        Number of verses inserted.
    """
    # ------------------------------------------------------------------
    # Parse XML
    # ------------------------------------------------------------------
    tree = ET.parse(xml_path)
    root = tree.getroot()

    translation_name = root.attrib.get('translation', 'Unknown')
    translation_id = xml_path.stem.lower()
    if translation_id.endswith('bible'):
        translation_id = translation_id[:-5]  # Remove "bible" suffix
    status = root.attrib.get('status', 'Unknown')

    # Determine language ISO code from filename
    iso_code = iso_from_filename(xml_path.name) or 'en'

    # ------------------------------------------------------------------
    # Delete existing DB and connect
    # ------------------------------------------------------------------
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA key = \"x'{encryption_key}'\"")

    # SQLCipher 4.x compatibility settings (must match Rust side)
    cursor.execute("PRAGMA cipher_page_size = 4096")
    cursor.execute("PRAGMA kdf_iter = 256000")
    cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
    cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")

    # ------------------------------------------------------------------
    # Create tables (existing schema unchanged)
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS translations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            language TEXT NOT NULL,
            language_name TEXT,
            description TEXT,
            download_url TEXT,
            legal_notice TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            translation_id TEXT NOT NULL,
            id INTEGER NOT NULL,
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            chapter_count INTEGER NOT NULL,
            testament TEXT NOT NULL,
            PRIMARY KEY (translation_id, id),
            FOREIGN KEY (translation_id) REFERENCES translations(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verses (
            translation_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY (translation_id, book_id, chapter, verse),
            FOREIGN KEY (translation_id, book_id) REFERENCES books(translation_id, id) ON DELETE CASCADE
        )
    ''')

    # ------------------------------------------------------------------
    # NEW: book_names table – native script + English for every book
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_names (
            book_id INTEGER NOT NULL,
            native  TEXT NOT NULL,
            english TEXT NOT NULL,
            PRIMARY KEY (book_id)
        )
    ''')

    # ------------------------------------------------------------------
    # Insert translation metadata (now with correct ISO language code)
    # ------------------------------------------------------------------
    cursor.execute('''
        INSERT OR REPLACE INTO translations (id, name, abbreviation, language, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (translation_id, translation_name, translation_id.upper(), iso_code, status))

    # ------------------------------------------------------------------
    # Process verses and track books
    # ------------------------------------------------------------------
    verses_to_insert = []
    books_map = {}  # book_id -> {name, testament, max_chapter}

    testaments = root.findall('testament')
    if testaments:
        for testament in testaments:
            testament_name = (testament.attrib.get('name')
                              or testament.attrib.get('number')
                              or 'Unknown')
            for book in testament.findall('book'):
                book_num = int(book.attrib.get('number'))
                book_name = book.attrib.get('name', f'Book {book_num}')

                if book_num not in books_map:
                    books_map[book_num] = {
                        'name': book_name,
                        'testament': testament_name,
                        'max_chapter': 0
                    }

                for chapter in book.findall('chapter'):
                    chapter_num = int(chapter.attrib.get('number'))
                    books_map[book_num]['max_chapter'] = max(
                        books_map[book_num]['max_chapter'], chapter_num)

                    for verse in chapter.findall('verse'):
                        verses_to_insert.append((
                            translation_id, book_num, chapter_num,
                            int(verse.attrib.get('number')), verse.text or ""
                        ))
    else:
        for book in root.findall('book'):
            book_num = int(book.attrib.get('number'))
            book_name = book.attrib.get('name', f'Book {book_num}')
            testament_name = "Old Testament" if book_num <= 39 else "New Testament"

            if book_num not in books_map:
                books_map[book_num] = {
                    'name': book_name,
                    'testament': testament_name,
                    'max_chapter': 0
                }

            for chapter in book.findall('chapter'):
                chapter_num = int(chapter.attrib.get('number'))
                books_map[book_num]['max_chapter'] = max(
                    books_map[book_num]['max_chapter'], chapter_num)

                for verse in chapter.findall('verse'):
                    verses_to_insert.append((
                        translation_id, book_num, chapter_num,
                        int(verse.attrib.get('number')), verse.text or ""
                    ))

    # Insert into books table
    books_to_insert = [
        (
            translation_id,
            book_id,
            info['name'],
            info['name'][:3].upper(),
            info['max_chapter'],
            info['testament']
        )
        for book_id, info in books_map.items()
    ]

    cursor.executemany('''
        INSERT OR REPLACE INTO books (translation_id, id, name, abbreviation, chapter_count, testament)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', books_to_insert)

    # Insert verses
    cursor.executemany('''
        INSERT OR REPLACE INTO verses (translation_id, book_id, chapter, verse, text)
        VALUES (?, ?, ?, ?, ?)
    ''', verses_to_insert)

    # ------------------------------------------------------------------
    # Populate book_names for books actually present in this translation
    # ------------------------------------------------------------------
    native_books = book_names_lookup.get(iso_code, {})
    book_names_to_insert = []
    for book_id in books_map:
        key = str(book_id)
        english_name = _ENGLISH_BOOK_NAMES.get(key, f'Book {book_id}')
        # Use native name if available, otherwise fall back to English
        native_name = native_books.get(key, english_name)
        book_names_to_insert.append((book_id, native_name, english_name))

    cursor.executemany('''
        INSERT OR REPLACE INTO book_names (book_id, native, english)
        VALUES (?, ?, ?)
    ''', book_names_to_insert)

    conn.commit()
    conn.close()
    return len(verses_to_insert)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    start_time = time.perf_counter()

    try:
        encryption_key = get_encryption_key()
        print(encryption_key)
        encryption_key = base64.b64decode(encryption_key).hex()
    except Exception as e:
        print(f"Error loading encryption key: {e}")
        exit(1)

    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    xml_dir = project_dir / "Holy-Bible-XML-Format"
    db_dir = project_dir / "database/translations"
    db_dir.mkdir(exist_ok=True)

    # Load book names lookup once — shared across all worker processes via closure
    book_names_lookup = load_book_names_lookup(project_dir)
    print(f"Loaded native book names for {len(book_names_lookup)} languages: "
          f"{', '.join(sorted(book_names_lookup.keys()))}")

    xml_files = list(xml_dir.glob("*.xml"))
    total_files = len(xml_files)
    print(f"Found {total_files} XML files. Starting parallel conversion...")

    completed = 0
    total_verses = 0

    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(
                convert_xml_to_db,
                xml_file,
                db_dir / f"{xml_file.stem}.db",
                encryption_key,
                book_names_lookup
            ): xml_file
            for xml_file in xml_files
        }

        for future in as_completed(futures):
            xml_file = futures[future]
            completed += 1
            try:
                verse_count = future.result()
                total_verses += verse_count
                if completed % 50 == 0 or completed == total_files:
                    print(f"Progress: {completed}/{total_files} files converted "
                          f"({total_verses:,} total verses).")
            except Exception as e:
                print(f"Failed to convert {xml_file.name}: {e}")

    end_time = time.perf_counter()
    print(f"\nFinal Summary:")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")
    print(f"Average time per file: {(end_time - start_time) / total_files:.4f} seconds")
    print(f"Total verses processed: {total_verses:,}")
