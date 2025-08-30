# HB_index

A comprehensive Bible translation index for Bible apps, providing access to 1000+ translations in 200+ languages.

## Features

- Index of 1000+ Bible translations from Holy-Bible-XML-Format repository
- Supports 200+ languages with native script names
- Testament coverage tracking (Old/New Testament availability)
- Direct download URLs for each translation
- File size information for storage planning

## Quick Start

```bash
# Generate the index
python generate_index.py

# Download a specific translation
python download_translation.py <translation-id>

# Update with latest translations
python update_index.py

# Validate index file
python validate_index.py
```

## Structure

- `bible-translations-index.json` - Main index file with all translation metadata
- `Holy-Bible-XML-Format/` - Git submodule containing XML Bible files
- Python utilities for index generation and maintenance

## Index Format

The index organizes translations by language with metadata including:
- Translation name and filename
- Testament coverage (complete Bible vs NT-only)
- File size and download URL
- Native language names for multilingual support

Perfect for Bible apps needing comprehensive translation access.