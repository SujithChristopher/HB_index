#!/usr/bin/env python3
"""Extract unique languages from bible-translations-index.json"""

import json

def extract_languages():
    with open('bible-translations-index.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    languages = []
    for lang_entry in data['languages']:
        languages.append({
            'language': lang_entry['language'],
            'native_name': lang_entry['native_name'],
            'iso_code': lang_entry.get('iso_code', '')
        })

    # Sort by language name
    languages.sort(key=lambda x: x['language'])

    print(f"Total languages: {len(languages)}\n")
    for lang in languages:
        print(f"{lang['language']:30} | {lang['native_name']:30} | {lang['iso_code']}")

    return languages

if __name__ == "__main__":
    languages = extract_languages()
