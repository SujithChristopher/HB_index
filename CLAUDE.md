# BibleDir Project

## Overview
This project creates a comprehensive Bible app with multiple translations in different languages. The main goal is to build an index file that helps the Bible app understand which translations are available for download and use.

## Project Structure
```
HB_index/
├── scripts/                        # Python utility scripts
│   ├── generate_index.py          # Generate index from XML files
│   ├── download_translation.py    # Download translations
│   ├── update_index.py            # Update and maintain index
│   ├── validate_index.py          # Validate index integrity
│   ├── convert_to_db.py           # Convert XML to encrypted SQLite DB
│   └── ...                        # Other utility scripts
├── database/
│   ├── metadata/                  # JSON metadata files (current)
│   │   ├── bible-translations-index.json
│   │   ├── bible-book-names.json
│   │   └── bible-book-names-template.json
│   └── *.db                       # Encrypted SQLite databases
├── Holy-Bible-XML-Format/         # Git submodule (1000+ XML translations)
├── bible-translations-index.json  # Legacy (root level, for backward compatibility)
├── .env                           # Encryption key for databases
├── CLAUDE.md                      # This documentation
└── .git/                          # Git repository
```

## Bible Translation Data
- **Source**: Holy-Bible-XML-Format git submodule
- **Format**: XML files with structure: `<bible><testament><book><chapter><verse>`
- **Languages**: 200+ languages with various scripts (Latin, Chinese, Hindi, Arabic, etc.)
- **Versions**: 1000+ different Bible versions/revisions
- **Coverage**: Some translations have full Bible, others only New Testament or missing books

## Translation Index Requirements
The `bible-translations-index.json` file should contain:

1. **Language Organization**: Sorted alphabetically by language
2. **Native Scripts**: Include language names in original script
3. **Testament Coverage**: Track Old Testament/New Testament availability
4. **Missing Content**: Note any missing books/chapters/verses
5. **Metadata**: Translation name, year, status, links, etc.

### JSON Structure
```json
{
  "languages": [
    {
      "language": "English",
      "native_name": "English",
      "iso_code": "en",
      "translations": [
        {
          "id": "english-kjv",
          "name": "King James Version",
          "filename": "EnglishKJBible.xml",
          "download_url": "https://raw.githubusercontent.com/SujithChristopher/Holy-Bible-XML-Format/master/EnglishKJBible.xml",
          "file_size_bytes": 4123456,
          "testament_coverage": {
            "old_testament": true,
            "new_testament": true,
            "total_books": 66
          },
          "metadata": {
            "status": "Public Domain",
            "year": null,
            "info": "",
            "site": "",
            "link": ""
          }
        }
      ]
    }
  ],
  "summary": {
    "total_languages": 324,
    "total_translations": 1045,
    "complete_bibles": 696,
    "new_testament_only": 319,
    "old_testament_only": 10,
    "total_size_bytes": 5242880000
  }
}
```

## Progress Status
- [x] Repository structure explored and reorganized
- [x] Scripts moved to `scripts/` directory
- [x] Metadata files moved to `database/metadata/`
- [x] Encrypted SQLite database conversion implemented
- [x] Comprehensive translation index with metadata
- [x] Download URLs and file size tracking
- [x] Testament coverage analysis
- [x] Maintenance and validation utilities

## Notes
- XML files use UTF-8 encoding
- Some translations are New Testament only (e.g., Chinese1886Bible.xml)
- Translation names are in the `translation` attribute
- Additional metadata in `status`, `info`, `site`, `link` attributes
- Format choice: JSON selected for app compatibility and ease of parsing

## Key Scripts (in `scripts/` directory)

| Script | Purpose |
|--------|---------|
| `generate_index.py` | Parse XML files and generate index at `database/metadata/bible-translations-index.json` |
| `convert_to_db.py` | Convert XML translations to encrypted SQLite databases |
| `download_translation.py` | Interactive search and download interface for translations |
| `update_index.py` | Maintenance: update submodule, regenerate index, show stats |
| `validate_index.py` | Validate index integrity and provide detailed analysis |
| `extract_languages.py` | Extract and list all languages from index |
| `collect_book_names.py` | Manage native book names across languages |
| `upload_to_s3.py` | Sync `database/` folder to AWS S3 bucket (tdb-bucket-stream) |

## File Paths
- **Metadata files**: `database/metadata/*.json` (current, updated by scripts)
- **Legacy files**: Root level `*.json` (backward compatibility, not touched)
- **Databases**: `database/*.db` (encrypted SQLite files)
- **Source data**: `Holy-Bible-XML-Format/` (git submodule)

## API Integration Notes
The index file format is designed for easy Bible app integration:

1. **Direct Downloads**: Each translation has a `download_url` for immediate access
2. **Size Planning**: `file_size_bytes` helps with storage and bandwidth planning
3. **Coverage Info**: `testament_coverage` indicates available content
4. **Native Scripts**: `native_name` field supports multilingual interfaces
5. **Searchable**: Unique IDs and structured metadata enable efficient searching

## Usage Examples

```python
# Load the index from new location
import json
with open('database/metadata/bible-translations-index.json', 'r', encoding='utf-8') as f:
    index = json.load(f)

# Find English translations
english_translations = next(
    (lang['translations'] for lang in index['languages']
     if lang['language'] == 'English'), []
)

# Get both XML and DB URLs
translation = english_translations[0]
print(f"XML URL: {translation['download_url']}")
print(f"DB URL: {translation.get('db_url')}")
print(f"Encrypted: {translation.get('encrypted', False)}")
```

## Python Development Setup

**Package Manager**: Always use `uv` for managing dependencies (faster and more reliable than pip)

```bash
# Install uv (if not already installed)
curl https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install boto3 python-dotenv

# Or use requirements file
uv pip install -r requirements.txt
```

## AWS S3 Sync Configuration

The `upload_to_s3.py` script syncs the `database/` folder to S3 automatically.

**Setup:**
1. Add AWS credentials to `.env` file:
   ```
   ACCESSKEY_ID=your_access_key
   SECRET_ACCESSKEY_ID=your_secret_key
   ```

2. Run sync:
   ```bash
   python scripts/upload_to_s3.py
   ```

**Options:**
- `--workers N`: Number of parallel upload threads (default: 4)
- `--prefix folder/`: S3 folder prefix (default: root)
- `--quiet`: Suppress verbose output

## Notes
- All Python scripts automatically resolve paths relative to project root
- `.env` file contains `ENCRYPTION_KEY` for SQLite database encryption and AWS credentials
- Legacy JSON files at root remain unchanged for backward compatibility
- Run scripts from any directory; they locate files via `__file__` resolution
- Always use `uv` instead of `pip` for faster, more reliable dependency management