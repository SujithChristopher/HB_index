#!/usr/bin/env python3
"""
Bible Translations Index Generator

This script scans the Holy-Bible-XML-Format directory and creates a comprehensive
index of all Bible translations with metadata and testament coverage information.
"""

import os
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
import re

def normalize_language_name(base_name):
    """Normalize language name to group related languages."""
    # List of base languages to check against
    base_languages = [
        'English', 'Chinese', 'Arabic', 'Spanish', 'French', 'German', 'Portuguese',
        'Russian', 'Korean', 'Japanese', 'Hindi', 'Tamil', 'Telugu', 'Bengali',
        'Gujarati', 'Marathi', 'Malayalam', 'Kannada', 'Punjabi', 'Urdu', 'Persian',
        'Turkish', 'Hebrew', 'Greek', 'Latin', 'Italian', 'Dutch', 'Swedish',
        'Norwegian', 'Danish', 'Finnish', 'Polish', 'Czech', 'Slovak', 'Hungarian',
        'Romanian', 'Bulgarian', 'Serbian', 'Croatian', 'Slovenian', 'Albanian',
        'Estonian', 'Latvian', 'Lithuanian', 'Ukrainian', 'Belarusian', 'Amharic',
        'Azerbaijan', 'Balochi', 'Chin', 'Fulfulde', 'Kurdish', 'Oromo', 'Romani',
        'Swahili', 'Twi', 'Armenian', 'Greek', 'Dinka', 'Indonesian', 'Kamba',
        'Karakalpak', 'Macedonian', 'Makonde'
    ]
    
    # Handle special cases and variations
    if base_name.startswith('Chin'):
        return 'Chin'
    if base_name.startswith('Original'):
        if 'Greek' in base_name:
            return 'Greek'
        if 'Hebrew' in base_name:
            return 'Hebrew'

    for lang in base_languages:
        if base_name.startswith(lang):
            return lang
            
    return base_name

def extract_language_from_filename(filename):
    """Extract language name from filename."""
    # Remove 'Bible.xml' and any year/version suffixes
    base_name = filename.replace('Bible.xml', '')
    base_name = re.sub(r'\d{4}', '', base_name)  # Remove years
    base_name = re.sub(r'[A-Z]{2,5}$', '', base_name)  # Remove version codes
    
    # Normalize the language name
    return normalize_language_name(base_name)

def get_language_info(language):
    """Get native name and ISO code for a language."""
    language_map = {
        'English': {'native': 'English', 'iso': 'en'},
        'Chinese': {'native': '中文', 'iso': 'zh'},
        'Arabic': {'native': 'العربية', 'iso': 'ar'},
        'Spanish': {'native': 'Español', 'iso': 'es'},
        'French': {'native': 'Français', 'iso': 'fr'},
        'German': {'native': 'Deutsch', 'iso': 'de'},
        'Portuguese': {'native': 'Português', 'iso': 'pt'},
        'Russian': {'native': 'Русский', 'iso': 'ru'},
        'Korean': {'native': '한국어', 'iso': 'ko'},
        'Japanese': {'native': '日本語', 'iso': 'ja'},
        'Hindi': {'native': 'हिन्दी', 'iso': 'hi'},
        'Tamil': {'native': 'தமிழ்', 'iso': 'ta'},
        'Telugu': {'native': 'తెలుగు', 'iso': 'te'},
        'Bengali': {'native': 'বাংলা', 'iso': 'bn'},
        'Gujarati': {'native': 'ગુજરાતી', 'iso': 'gu'},
        'Marathi': {'native': 'मराठी', 'iso': 'mr'},
        'Malayalam': {'native': 'മലയാളം', 'iso': 'ml'},
        'Kannada': {'native': 'ಕನ್ನಡ', 'iso': 'kn'},
        'Punjabi': {'native': 'ਪੰਜਾਬੀ', 'iso': 'pa'},
        'Urdu': {'native': 'اردو', 'iso': 'ur'},
        'Persian': {'native': 'فارسی', 'iso': 'fa'},
        'Turkish': {'native': 'Türkçe', 'iso': 'tr'},
        'Hebrew': {'native': 'עברית', 'iso': 'he'},
        'Greek': {'native': 'Ελληνικά', 'iso': 'el'},
        'Latin': {'native': 'Latina', 'iso': 'la'},
        'Italian': {'native': 'Italiano', 'iso': 'it'},
        'Dutch': {'native': 'Nederlands', 'iso': 'nl'},
        'Swedish': {'native': 'Svenska', 'iso': 'sv'},
        'Norwegian': {'native': 'Norsk', 'iso': 'no'},
        'Danish': {'native': 'Dansk', 'iso': 'da'},
        'Finnish': {'native': 'Suomi', 'iso': 'fi'},
        'Polish': {'native': 'Polski', 'iso': 'pl'},
        'Czech': {'native': 'Čeština', 'iso': 'cs'},
        'Slovak': {'native': 'Slovenčina', 'iso': 'sk'},
        'Hungarian': {'native': 'Magyar', 'iso': 'hu'},
        'Romanian': {'native': 'Română', 'iso': 'ro'},
        'Bulgarian': {'native': 'Български', 'iso': 'bg'},
        'Serbian': {'native': 'Српски', 'iso': 'sr'},
        'Croatian': {'native': 'Hrvatski', 'iso': 'hr'},
        'Slovenian': {'native': 'Slovenščina', 'iso': 'sl'},
        'Albanian': {'native': 'Shqip', 'iso': 'sq'},
        'Estonian': {'native': 'Eesti', 'iso': 'et'},
        'Latvian': {'native': 'Latviešu', 'iso': 'lv'},
        'Lithuanian': {'native': 'Lietuvių', 'iso': 'lt'},
        'Ukrainian': {'native': 'Українська', 'iso': 'uk'},
        'Belarusian': {'native': 'Беларуская', 'iso': 'be'},
    }
    
    return language_map.get(language, {'native': language, 'iso': None})

def generate_translation_id(filename):
    """Generate a unique ID from filename."""
    # Remove 'Bible.xml' and convert to lowercase kebab-case
    base_name = filename.replace('Bible.xml', '').lower()
    # Replace numbers and uppercase patterns with hyphens
    base_name = re.sub(r'([a-z])([A-Z0-9])', r'\1-\2', base_name).lower()
    # Clean up multiple hyphens
    base_name = re.sub(r'-+', '-', base_name).strip('-')
    return base_name

def parse_bible_file(filepath):
    """Parse a Bible XML file and extract metadata."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Extract metadata from root bible element
        translation_name = root.get('translation', '')
        status = root.get('status', '')
        info = root.get('info', '')
        site = root.get('site', '')
        link = root.get('link', '')
        
        # Check testament coverage
        testaments = root.findall('testament')
        has_old_testament = any(t.get('name') == 'Old' for t in testaments)
        has_new_testament = any(t.get('name') == 'New' for t in testaments)
        
        # Count total books
        total_books = 0
        for testament in testaments:
            books = testament.findall('book')
            total_books += len(books)
        
        return {
            'translation_name': translation_name,
            'has_old_testament': has_old_testament,
            'has_new_testament': has_new_testament,
            'total_books': total_books,
            'status': status,
            'info': info,
            'site': site,
            'link': link
        }
    except ET.ParseError as e:
        print(f"Warning: Could not parse {filepath}: {e}")
        return None
    except Exception as e:
        print(f"Warning: Error processing {filepath}: {e}")
        return None

def generate_bible_index(bible_dir):
    """Generate the complete Bible translations index."""
    if not os.path.exists(bible_dir):
        raise FileNotFoundError(f"Bible directory not found: {bible_dir}")
    
    # Group translations by language
    languages_data = defaultdict(list)
    
    # Scan all XML files
    xml_files = [f for f in os.listdir(bible_dir) if f.endswith('Bible.xml')]
    print(f"Found {len(xml_files)} Bible translation files")
    
    processed_count = 0
    for filename in xml_files:
        filepath = os.path.join(bible_dir, filename)
        
        # Extract language from filename
        language = extract_language_from_filename(filename)
        
        # Parse the XML file and get file size
        bible_data = parse_bible_file(filepath)
        if bible_data is None:
            continue
        
        # Get file size in bytes
        file_size = os.path.getsize(filepath)
        
        # Get DB size if it exists
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_filepath = os.path.join(project_dir, 'database', filename.replace('.xml', '.db'))
        db_file_size = os.path.getsize(db_filepath) if os.path.exists(db_filepath) else 0
        
        # Determine if this is a Protestant canon (66 books with both testaments)
        is_protestant = (
            bible_data['total_books'] == 66 and
            bible_data['has_old_testament'] and
            bible_data['has_new_testament']
        )

        # Create translation entry
        db_filename = filename.replace('.xml', '.db')
        translation_entry = {
            'id': generate_translation_id(filename),
            'name': bible_data['translation_name'] or filename.replace('Bible.xml', ''),
            'filename': filename,
            'download_url': f'https://raw.githubusercontent.com/SujithChristopher/Holy-Bible-XML-Format/master/{filename}',
            'db_url': f'https://github.com/SujithChristopher/HB_index/releases/download/databases/{db_filename}',
            'file_size_bytes': file_size,
            'testament_coverage': {
                'old_testament': bible_data['has_old_testament'],
                'new_testament': bible_data['has_new_testament'],
                'total_books': bible_data['total_books']
            },
            'protestant': is_protestant,
            'encrypted': True,
            'db_file_size_bytes': db_file_size,
            'metadata': {
                'status': bible_data['status'],
                'year': None,  # Could be extracted from info or status if needed
                'info': bible_data['info'],
                'site': bible_data['site'],
                'link': bible_data['link']
            }
        }
        
        languages_data[language].append(translation_entry)
        processed_count += 1
        
        if processed_count % 50 == 0:
            print(f"Processed {processed_count} files...")
    
    print(f"Successfully processed {processed_count} files")
    
    # Build final structure
    languages_list = []
    total_translations = 0
    complete_bibles = 0
    new_testament_only = 0
    old_testament_only = 0
    protestant_canon = 0
    total_size_bytes = 0

    for language, translations in sorted(languages_data.items()):
        language_info = get_language_info(language)

        # Sort translations by name
        translations.sort(key=lambda x: x['name'])

        # Count statistics for this language
        for trans in translations:
            total_translations += 1
            total_size_bytes += trans['file_size_bytes']
            coverage = trans['testament_coverage']
            if coverage['old_testament'] and coverage['new_testament']:
                complete_bibles += 1
            elif coverage['new_testament'] and not coverage['old_testament']:
                new_testament_only += 1
            elif coverage['old_testament'] and not coverage['new_testament']:
                old_testament_only += 1

            # Count Protestant canon translations
            if trans['protestant']:
                protestant_canon += 1
        
        languages_list.append({
            'language': language,
            'native_name': language_info['native'],
            'iso_code': language_info['iso'],
            'translations': translations
        })
    
    # Create final index structure
    index = {
        'languages': languages_list,
        'summary': {
            'total_languages': len(languages_list),
            'total_translations': total_translations,
            'complete_bibles': complete_bibles,
            'new_testament_only': new_testament_only,
            'old_testament_only': old_testament_only,
            'protestant_canon': protestant_canon,
            'total_size_bytes': total_size_bytes
        }
    }
    
    return index

def main():
    """Main function to generate the Bible translations index."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    bible_dir = os.path.join(project_dir, 'Holy-Bible-XML-Format')
    output_file = os.path.join(project_dir, 'database', 'metadata', 'bible-translations-index.json')
    
    print("Bible Translations Index Generator")
    print("=" * 40)
    print(f"Scanning directory: {bible_dir}")
    
    try:
        # Generate the index
        index = generate_bible_index(bible_dir)
        
        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        # Helper function to format file size
        def format_size(size_bytes):
            if size_bytes >= 1024**3:
                return f"{size_bytes / (1024**3):.1f} GB"
            elif size_bytes >= 1024**2:
                return f"{size_bytes / (1024**2):.1f} MB"
            elif size_bytes >= 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes} bytes"
        
        print(f"\nIndex generated successfully!")
        print(f"Output file: {output_file}")
        print(f"\nSummary:")
        print(f"- Total languages: {index['summary']['total_languages']}")
        print(f"- Total translations: {index['summary']['total_translations']}")
        print(f"- Complete Bibles: {index['summary']['complete_bibles']}")
        print(f"- New Testament only: {index['summary']['new_testament_only']}")
        print(f"- Old Testament only: {index['summary']['old_testament_only']}")
        print(f"- Protestant canon (66 books): {index['summary']['protestant_canon']}")
        print(f"- Total size: {format_size(index['summary']['total_size_bytes'])}")
        
    except Exception as e:
        print(f"Error generating index: {e}")
        raise

if __name__ == '__main__':
    main()