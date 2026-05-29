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
# Common entrypoint
python scripts/hb_index.py --help

# Convert XML to encrypted DBs, generate metadata, and upload database/
python scripts/hb_index.py build

# Generate the index only
python scripts/hb_index.py index

# Validate index file
python scripts/hb_index.py validate

# Download a specific translation
python scripts/hb_index.py download <translation-id>

# Verify sample S3/GitHub downloads
python scripts/hb_index.py test-download --count 2
```

## Structure

- `bible-translations-index.json` - Main index file with all translation metadata
- `Holy-Bible-XML-Format/` - Git submodule containing XML Bible files
- `database/` - generated encrypted DBs and metadata used for release uploads
- `scripts/` - workflow and maintenance scripts
- `tests/` - executable checks and analysis scripts

### Script Groups

- Release pipeline: `scripts/build_and_upload.py`, routed by `scripts/hb_index.py build`
- Upload/download: `scripts/upload_to_s3.py`, `scripts/download_translation.py`
- Validation/checks: `scripts/validate_index.py`, `tests/test_download.py`,
  `tests/test_incremental_sync.py`
- Metadata maintenance: `scripts/generate_index.py`, `scripts/update_index.py`,
  `scripts/update_index_classifications.py`, book-name helper scripts

## Index Format

The index organizes translations by language with metadata including:
- Translation name and filename
- Testament coverage (complete Bible vs NT-only)
- File size and download URL
- Native language names for multilingual support

Perfect for Bible apps needing comprehensive translation access.
