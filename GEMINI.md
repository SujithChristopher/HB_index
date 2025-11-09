# Project Overview

This project is a Python-based system for managing a comprehensive index of over 1000 Bible translations in more than 200 languages. The core of the project is the `bible-translations-index.json` file, which contains metadata for each translation, including testament coverage, download URLs, and file sizes. The translations themselves are sourced from the `Holy-Bible-XML-Format` git submodule, which contains the Bible texts in XML format.

The project provides a suite of Python scripts for managing the index:

- `generate_index.py`: Scans the `Holy-Bible-XML-Format` directory and generates the `bible-translations-index.json` file.
- `update_index.py`: Updates the `Holy-Bible-XML-Format` submodule and regenerates the index.
- `download_translation.py`: Allows users to download specific Bible translations from the index.
- `validate_index.py`: Validates the `bible-translations-index.json` file and provides detailed analysis of the data.

# Building and Running

This project does not have a traditional build process. The main artifacts are the Python scripts and the `bible-translations-index.json` file.

## Key Commands

To get started, you need to have Python installed. Then, you can use the following commands:

- **Generate the index:**
  ```bash
  python generate_index.py
  ```

- **Update the index with the latest translations:**
  ```bash
  python update_index.py
  ```

- **Download a specific translation:**
  ```bash
  python download_translation.py <translation-id>
  ```
  You can also run the script in interactive mode to search for and download translations:
  ```bash
  python download_translation.py
  ```

- **Validate the index file:**
  ```bash
  python validate_index.py
  ```

# Development Conventions

The project follows standard Python coding conventions. The code is well-documented with comments and docstrings. The main data format is JSON, which is used for the `bible-translations-index.json` file. The Bible translations themselves are in XML format.

The project is organized into a set of single-purpose scripts, which makes it easy to understand and maintain. The use of a git submodule for the Bible translations ensures that the data is kept up-to-date with the upstream repository.
