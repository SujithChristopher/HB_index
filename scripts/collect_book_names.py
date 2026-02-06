#!/usr/bin/env python3
"""
Script to collect native Bible book names for different languages.
This script will be used in conjunction with web searches to populate the bible-book-names.json file.
"""

import json
import sys
import os

def get_project_dir():
    """Get the project root directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)

def load_template():
    """Load the template file"""
    project_dir = get_project_dir()
    template_file = os.path.join(project_dir, 'database', 'metadata', 'bible-book-names-template.json')
    with open(template_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_languages():
    """Load languages from the translations index"""
    project_dir = get_project_dir()
    index_file = os.path.join(project_dir, 'database', 'metadata', 'bible-translations-index.json')
    with open(index_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    languages = []
    for lang_entry in data['languages']:
        languages.append({
            'language': lang_entry['language'],
            'native_name': lang_entry['native_name'],
            'iso_code': lang_entry.get('iso_code', ''),
            'translation_count': len(lang_entry['translations'])
        })

    return languages

def add_language_books(language_code, language_name, native_name, book_names_dict):
    """
    Add book names for a language.
    book_names_dict should be a dictionary with book numbers (1-66) as keys and native names as values.
    """
    data = load_template()
    project_dir = get_project_dir()
    book_names_file = os.path.join(project_dir, 'database', 'metadata', 'bible-book-names.json')

    # Load existing data if available
    try:
        with open(book_names_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        pass

    # Create language entry
    if language_code not in data['languages']:
        data['languages'][language_code] = {
            'language': language_name,
            'native_name': native_name,
            'books': {}
        }

    # Add book names
    for book_num, native_book_name in book_names_dict.items():
        # Get English name for reference
        english_name = ""
        all_books = data['book_order']['old_testament'] + data['book_order']['new_testament']
        for book in all_books:
            if book['number'] == int(book_num):
                english_name = book['english_name']
                break

        data['languages'][language_code]['books'][str(book_num)] = {
            'native_name': native_book_name,
            'english_name': english_name
        }

    # Save updated data
    with open(book_names_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Added {len(book_names_dict)} books for {language_name} ({native_name})")

def get_priority_languages():
    """Get priority languages based on translation count and global usage"""
    languages = load_languages()

    # Major world languages
    major_languages = [
        'English', 'Spanish', 'French', 'German', 'Italian', 'Portuguese',
        'Russian', 'Chinese', 'Japanese', 'Korean', 'Arabic', 'Hebrew',
        'Hindi', 'Bengali', 'Tamil', 'Telugu', 'Malayalam', 'Kannada',
        'Marathi', 'Gujarati', 'Urdu', 'Punjabi', 'Indonesian', 'Vietnamese',
        'Thai', 'Turkish', 'Polish', 'Dutch', 'Greek', 'Persian', 'Swahili'
    ]

    priority = []
    for lang in languages:
        if lang['language'] in major_languages:
            priority.append(lang)

    # Sort by translation count
    priority.sort(key=lambda x: x['translation_count'], reverse=True)

    return priority

def print_priority_list():
    """Print the priority list of languages to research"""
    priority = get_priority_languages()

    print("Priority Languages for Native Book Names Research:")
    print("=" * 80)
    print(f"{'Language':<30} {'Native Name':<30} {'ISO':<5} {'Translations'}")
    print("-" * 80)

    for lang in priority:
        iso = lang['iso_code'] if lang['iso_code'] else ''
        print(f"{lang['language']:<30} {lang['native_name']:<30} {iso:<5} {lang['translation_count']}")

    print(f"\nTotal: {len(priority)} priority languages")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print_priority_list()
    else:
        print("Usage:")
        print("  python3 collect_book_names.py list  - Show priority languages")
        print("\nTo add book names programmatically:")
        print("  from collect_book_names import add_language_books")
        print("  add_language_books('en', 'English', 'English', {1: 'Genesis', 2: 'Exodus', ...})")
