# BibleDir Project

## Overview
This project creates a comprehensive Bible app with multiple translations in different languages. The main goal is to build an index file that helps the Bible app understand which translations are available for download and use.

## Project Structure
```
BibleDir/
├── Holy-Bible-XML-Format/          # Git submodule with 1000+ Bible translations
├── bible-translations-index.json   # Main index file (to be created)
├── CLAUDE.md                       # This documentation
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
- [x] Repository structure explored
- [x] Git repository initialized
- [x] Added Holy-Bible-XML-Format as submodule
- [x] Analyzed sample translation files
- [x] Designed file format and schema
- [x] Created project documentation
- [x] Created comprehensive translation index file
- [x] Added individual download URLs for each translation
- [x] Added file size information for storage planning
- [x] Created maintenance utilities

## Notes
- XML files use UTF-8 encoding
- Some translations are New Testament only (e.g., Chinese1886Bible.xml)
- Translation names are in the `translation` attribute
- Additional metadata in `status`, `info`, `site`, `link` attributes
- Format choice: JSON selected for app compatibility and ease of parsing

## Utility Scripts

### `generate_index.py`
Main script to create the comprehensive Bible translations index:
- Scans all XML files in Holy-Bible-XML-Format directory
- Extracts metadata, testament coverage, and file sizes
- Generates bible-translations-index.json with download URLs
- Supports periodic updates as new translations are added

### `download_translation.py`
Utility for downloading individual translations:
- Interactive search and download interface
- Command-line mode: `python download_translation.py <translation-id>`
- Progress indication during downloads
- Creates downloads/ directory for files

### `update_index.py`
Maintenance utility for keeping the index current:
- Update git submodule with latest translations
- Regenerate index file
- Show current statistics
- Search functionality

### `validate_index.py`
Validation and analysis tool:
- Verifies index file structure and data integrity
- Provides detailed statistics and analysis
- Interactive language exploration

## API Integration Notes
The index file format is designed for easy Bible app integration:

1. **Direct Downloads**: Each translation has a `download_url` for immediate access
2. **Size Planning**: `file_size_bytes` helps with storage and bandwidth planning
3. **Coverage Info**: `testament_coverage` indicates available content
4. **Native Scripts**: `native_name` field supports multilingual interfaces
5. **Searchable**: Unique IDs and structured metadata enable efficient searching

## Usage Examples

```python
# Load the index
import json
with open('bible-translations-index.json', 'r', encoding='utf-8') as f:
    index = json.load(f)

# Find English translations
english_translations = next(
    (lang['translations'] for lang in index['languages'] 
     if lang['language'] == 'English'), []
)

# Download a specific translation
import requests
translation = english_translations[0]  # First English translation
response = requests.get(translation['download_url'])
with open(translation['filename'], 'wb') as f:
    f.write(response.content)
```