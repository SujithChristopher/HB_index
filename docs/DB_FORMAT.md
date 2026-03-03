# Bible DB Format

Each Bible translation is stored as an individual **encrypted SQLite database** (`.db`) file, produced by `scripts/convert_to_db.py`. The database is encrypted with **SQLCipher 4** using a shared key stored in `.env`.

---

## File Location & Naming

```
database/
└── translations/
    ├── TamilBible.db
    ├── HindiBible.db
    ├── EnglishKJBible.db
    └── ...  (one .db per XML source file)
```

- Filename mirrors the source XML: `{Name}Bible.xml` → `{Name}Bible.db`
- `translation_id` (primary key used inside the DB) strips the `Bible` suffix and lowercases it:
  `TamilBible.db` → `"tamil"`, `EnglishKJBible.db` → `"englishkj"`

---

## Encryption

| Parameter | Value |
|-----------|-------|
| Engine | SQLCipher 4 |
| Key format | Raw hex (`x'<hex>'`) derived by base64-decoding `ENCRYPTION_KEY` from `.env` |
| `cipher_page_size` | 4096 |
| `kdf_iter` | 256000 |
| `cipher_hmac_algorithm` | HMAC_SHA512 |
| `cipher_kdf_algorithm` | PBKDF2_HMAC_SHA512 |

Every connection must apply these PRAGMAs **before** any query:

```python
cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")
cursor.execute("PRAGMA cipher_page_size = 4096")
cursor.execute("PRAGMA kdf_iter = 256000")
cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
```

---

## Tables

### `translations`

Top-level translation metadata. Always exactly **one row** per DB.

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | Short identifier, e.g. `"tamil"`, `"englishkj"` |
| `name` | TEXT | Full translation name from XML `translation` attribute |
| `abbreviation` | TEXT | Uppercase of `id`, e.g. `"TAMIL"` |
| `language` | TEXT | ISO 639-1 code, e.g. `"ta"`, `"hi"`, `"en"` |
| `language_name` | TEXT | *(reserved, currently NULL)* |
| `description` | TEXT | Status string from XML `status` attribute |
| `download_url` | TEXT | *(reserved, currently NULL)* |
| `legal_notice` | TEXT | *(reserved, currently NULL)* |

---

### `books`

One row per book present in this translation.

| Column | Type | Description |
|--------|------|-------------|
| `translation_id` | TEXT FK | References `translations.id` |
| `id` | INTEGER | Canonical book number (1–66, Protestant order) |
| `name` | TEXT | Book name string from XML (often `"Book N"` — see `book_names` for native names) |
| `abbreviation` | TEXT | First 3 chars of `name`, uppercased |
| `chapter_count` | INTEGER | Highest chapter number seen in the XML |
| `testament` | TEXT | `"Old"` / `"New"` (or value of `name`/`number` attr on `<testament>` element) |

> **Note:** Not all translations contain all 66 books. NT-only translations will have `id` values 40–66 only.

---

### `verses`

All verse text. This is the largest table.

| Column | Type | Description |
|--------|------|-------------|
| `translation_id` | TEXT FK | References `translations.id` |
| `book_id` | INTEGER FK | References `books.id` |
| `chapter` | INTEGER | Chapter number (1-based) |
| `verse` | INTEGER | Verse number (1-based) |
| `text` | TEXT | Verse text in the translation's native script |

Primary key: `(translation_id, book_id, chapter, verse)`

---

### `book_names` *(added 2026-03-01)*

Native-script and English book names for every book present in this translation. Used by Bible apps to display book names without requiring a separate lookup table.

| Column | Type | Description |
|--------|------|-------------|
| `book_id` | INTEGER PK | Canonical book number (1–66) |
| `native` | TEXT | Book name in the translation's native script |
| `english` | TEXT | Book name in English (always populated) |

**Source:** `bible-book-names.json`, keyed by the translation's ISO language code.  
**Fallback:** If the language is not yet in `bible-book-names.json`, both `native` and `english` contain the standard English name.

#### Example rows (TamilBible.db, `language='ta'`)

| `book_id` | `native` | `english` |
|-----------|----------|-----------|
| 1 | ஆதியாகமம் | Genesis |
| 19 | சங்கீதம் | Psalms |
| 40 | மத்தேயு | Matthew |
| 66 | வெளிப்படுத்தின விசேஷம் | Revelation |

---

## Entity Relationship

```
translations (1)
    │
    ├──< books (many)          [translation_id → translations.id]
    │       │
    │       └──< verses (many) [translation_id, book_id → books]
    │
    └──< book_names (many)     [book_id only — no FK, standalone lookup]
```

> `book_names` is intentionally **not** foreign-keyed to `books` so it can be queried independently without joining through `translations`.

---

## Book Numbering (Protestant Canon)

Books are numbered 1–66 in canonical Protestant order:

| Range | Testament |
|-------|-----------|
| 1–39 | Old Testament |
| 40–66 | New Testament |

Key reference points: `1` = Genesis, `19` = Psalms, `40` = Matthew, `66` = Revelation.

---

## Generating the DBs

```bash
# Generate all DBs from XML source files
uv run python scripts/convert_to_db.py
```

- Reads all `Holy-Bible-XML-Format/*.xml` files
- Loads `bible-book-names.json` once at startup (shared across all workers)
- Runs in parallel via `ProcessPoolExecutor`
- Outputs to `database/translations/`

**To add native book names for a new language:**
1. Add the language entry to `bible-book-names.json` (with ISO code key)
2. Re-run `convert_to_db.py` — the new names are picked up automatically

---

## Querying (Python example)

```python
import sqlcipher3 as sqlite3
import base64

with open('.env') as f:
    for line in f:
        if line.startswith('ENCRYPTION_KEY='):
            key = base64.b64decode(line.strip().split('=', 1)[1]).hex()

conn = sqlite3.connect('database/translations/TamilBible.db')
cur = conn.cursor()
cur.execute(f"PRAGMA key = \"x'{key}'\"")
cur.execute("PRAGMA cipher_page_size = 4096")
cur.execute("PRAGMA kdf_iter = 256000")
cur.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
cur.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")

# Get native book names
cur.execute("SELECT book_id, native, english FROM book_names ORDER BY book_id")
books = cur.fetchall()

# Get a verse
cur.execute("SELECT text FROM verses WHERE book_id=43 AND chapter=3 AND verse=16")
print(cur.fetchone()[0])  # John 3:16 in Tamil
```
