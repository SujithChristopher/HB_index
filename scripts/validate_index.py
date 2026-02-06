#!/usr/bin/env python3
"""
Bible Translations Index Validator

This script validates the generated bible-translations-index.json file
and provides detailed analysis of the translations data.
"""

import json
import os
from collections import Counter

def load_index(file_path):
    """Load and parse the Bible translations index."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_index(index):
    """Validate the structure and data of the index."""
    print("Index Structure Validation")
    print("=" * 40)
    
    # Check top-level structure
    required_keys = ['languages', 'summary']
    for key in required_keys:
        if key not in index:
            print(f"❌ Missing required key: {key}")
            return False
        else:
            print(f"✅ Found required key: {key}")
    
    # Validate summary
    summary = index['summary']
    summary_keys = ['total_languages', 'total_translations', 'complete_bibles', 'new_testament_only', 'old_testament_only']
    for key in summary_keys:
        if key not in summary:
            print(f"❌ Missing summary key: {key}")
        else:
            print(f"✅ Summary has {key}: {summary[key]}")
    
    # Check if summary matches actual data
    languages = index['languages']
    actual_language_count = len(languages)
    actual_translation_count = sum(len(lang['translations']) for lang in languages)
    
    print(f"\nData Validation:")
    print(f"Summary says {summary['total_languages']} languages, found {actual_language_count}")
    print(f"Summary says {summary['total_translations']} translations, found {actual_translation_count}")
    
    if summary['total_languages'] != actual_language_count:
        print("❌ Language count mismatch!")
    if summary['total_translations'] != actual_translation_count:
        print("❌ Translation count mismatch!")
    
    return True

def analyze_index(index):
    """Provide detailed analysis of the index data."""
    print("\n\nDetailed Analysis")
    print("=" * 40)
    
    languages = index['languages']
    
    # Top languages by translation count
    language_counts = [(lang['language'], len(lang['translations'])) for lang in languages]
    language_counts.sort(key=lambda x: x[1], reverse=True)
    
    print("\nTop 15 Languages by Translation Count:")
    for i, (lang, count) in enumerate(language_counts[:15], 1):
        print(f"{i:2d}. {lang:<20} {count:3d} translations")
    
    # Testament coverage analysis
    complete_count = 0
    nt_only_count = 0
    ot_only_count = 0
    
    for lang in languages:
        for trans in lang['translations']:
            coverage = trans['testament_coverage']
            if coverage['old_testament'] and coverage['new_testament']:
                complete_count += 1
            elif coverage['new_testament'] and not coverage['old_testament']:
                nt_only_count += 1
            elif coverage['old_testament'] and not coverage['new_testament']:
                ot_only_count += 1
    
    print(f"\nTestament Coverage:")
    print(f"Complete Bibles (OT+NT): {complete_count}")
    print(f"New Testament Only:     {nt_only_count}")
    print(f"Old Testament Only:     {ot_only_count}")
    
    # Languages with native scripts
    native_script_langs = []
    for lang in languages:
        if lang['language'] != lang['native_name']:
            native_script_langs.append((lang['language'], lang['native_name']))
    
    print(f"\nLanguages with Native Scripts ({len(native_script_langs)}):")
    for eng_name, native_name in sorted(native_script_langs)[:10]:
        print(f"  {eng_name} → {native_name}")
    if len(native_script_langs) > 10:
        print(f"  ... and {len(native_script_langs) - 10} more")
    
    # Sample some translations
    print(f"\nSample Translations:")
    sample_count = 0
    for lang in languages[:5]:
        for trans in lang['translations'][:2]:
            print(f"  {lang['language']}: {trans['name']} ({trans['filename']})")
            sample_count += 1
            if sample_count >= 10:
                break
        if sample_count >= 10:
            break

def show_language_details(index, language_name):
    """Show detailed information for a specific language."""
    for lang in index['languages']:
        if lang['language'].lower() == language_name.lower():
            print(f"\nLanguage Details: {lang['language']}")
            print(f"Native Name: {lang['native_name']}")
            print(f"ISO Code: {lang['iso_code']}")
            print(f"Total Translations: {len(lang['translations'])}")
            
            print(f"\nTranslations:")
            for i, trans in enumerate(lang['translations'], 1):
                coverage = trans['testament_coverage']
                testament_info = []
                if coverage['old_testament']:
                    testament_info.append("OT")
                if coverage['new_testament']:
                    testament_info.append("NT")
                testament_str = "+".join(testament_info) if testament_info else "None"
                
                print(f"{i:2d}. {trans['name']:<40} [{testament_str}] ({trans['filename']})")
                if trans['metadata']['status']:
                    print(f"     Status: {trans['metadata']['status']}")
            return
    
    print(f"Language '{language_name}' not found in index.")

def main():
    """Main function to validate and analyze the Bible translations index."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    index_file = os.path.join(project_dir, 'database', 'metadata', 'bible-translations-index.json')
    
    if not os.path.exists(index_file):
        print(f"Index file not found: {index_file}")
        print("Please run generate_index.py first to create the index.")
        return
    
    # Load and validate the index
    print("Bible Translations Index Validator")
    print("=" * 50)
    
    index = load_index(index_file)
    validate_index(index)
    analyze_index(index)
    
    # Interactive mode for exploring specific languages
    print(f"\nInteractive Mode:")
    print(f"Enter a language name to see details, or 'quit' to exit:")
    
    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            elif user_input:
                show_language_details(index, user_input)
            else:
                print("Available languages:", ", ".join([lang['language'] for lang in index['languages'][:20]]), "...")
        except KeyboardInterrupt:
            break
    
    print("\nValidation completed!")

if __name__ == '__main__':
    main()