#!/usr/bin/env python3
"""
Bible Translation Downloader

This script allows you to download individual Bible translations using the index file.
"""

import json
import os
import requests
from urllib.parse import urlparse
import sys

def load_index():
    """Load the Bible translations index."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    index_file = os.path.join(project_dir, 'database', 'metadata', 'bible-translations-index.json')
    if not os.path.exists(index_file):
        print("Error: bible-translations-index.json not found!")
        print("Please run generate_index.py first.")
        return None

    with open(index_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def format_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes >= 1024**3:
        return f"{size_bytes / (1024**3):.1f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / (1024**2):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} bytes"

def search_translations(index, query):
    """Search for translations matching the query."""
    query_lower = query.lower()
    results = []
    
    for lang in index['languages']:
        # Check language name match
        if query_lower in lang['language'].lower() or query_lower in lang['native_name'].lower():
            for trans in lang['translations']:
                results.append((lang, trans))
        else:
            # Check translation name match
            for trans in lang['translations']:
                if query_lower in trans['name'].lower() or query_lower in trans['id'].lower():
                    results.append((lang, trans))
    
    return results

def download_translation(url, filename, file_size):
    """Download a translation file with progress indication."""
    try:
        print(f"Downloading {filename} ({format_size(file_size)})...")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Create downloads directory if it doesn't exist
        os.makedirs('downloads', exist_ok=True)
        file_path = os.path.join('downloads', filename)
        
        downloaded = 0
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Simple progress indication
                    progress = (downloaded / file_size) * 100
                    print(f"\rProgress: {progress:.1f}%", end='', flush=True)
        
        print(f"\n✓ Downloaded successfully: {file_path}")
        return file_path
        
    except requests.RequestException as e:
        print(f"\n✗ Download failed: {e}")
        return None
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None

def download_by_id(index, translation_id):
    """Download a translation by its ID."""
    for lang in index['languages']:
        for trans in lang['translations']:
            if trans['id'] == translation_id:
                return download_translation(
                    trans['download_url'], 
                    trans['filename'], 
                    trans['file_size_bytes']
                )
    
    print(f"Translation with ID '{translation_id}' not found.")
    return None

def interactive_search_and_download(index):
    """Interactive search and download interface."""
    print("\nBible Translation Downloader")
    print("=" * 40)
    print("Enter search terms to find translations, or 'quit' to exit")
    
    while True:
        try:
            query = input("\nSearch: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
            
            # Search for translations
            results = search_translations(index, query)
            
            if not results:
                print("No translations found.")
                continue
            
            print(f"\nFound {len(results)} translations:")
            print("-" * 80)
            
            for i, (lang, trans) in enumerate(results[:20], 1):  # Show max 20 results
                coverage = []
                if trans['testament_coverage']['old_testament']:
                    coverage.append('OT')
                if trans['testament_coverage']['new_testament']:
                    coverage.append('NT')
                coverage_str = '+'.join(coverage) if coverage else 'None'
                
                size_str = format_size(trans['file_size_bytes'])
                print(f"{i:2d}. [{trans['id']}] {lang['language']}: {trans['name']}")
                print(f"    Coverage: {coverage_str} | Size: {size_str}")
            
            if len(results) > 20:
                print(f"... and {len(results) - 20} more results")
            
            # Ask user to select a translation and format
            try:
                choice = input("\nEnter number to download (or Enter to search again): ").strip()
                if choice:
                    choice_num = int(choice)
                    if 1 <= choice_num <= min(len(results), 20):
                        lang, trans = results[choice_num - 1]
                        
                        # Offer format choice if DB is available
                        format_choice = '1'
                        if 'db_url' in trans:
                            print(f"\nAvailable formats for {trans['name']}:")
                            print(f"  1. XML Source ({format_size(trans['file_size_bytes'])})")
                            print(f"  2. Encrypted SQLite DB ({format_size(trans.get('db_file_size_bytes', 0))})")
                            format_choice = input("Select format [1/2] (default 2): ").strip() or '2'
                        
                        if format_choice == '1':
                            download_translation(
                                trans['download_url'],
                                trans['filename'],
                                trans['file_size_bytes']
                            )
                        else:
                            db_filename = trans['filename'].replace('.xml', '.db')
                            download_translation(
                                trans['db_url'],
                                db_filename,
                                trans.get('db_file_size_bytes', 0)
                            )
                    else:
                        print("Invalid choice.")
            except ValueError:
                continue
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break

def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Command line mode - download by ID
        translation_id = sys.argv[1]
        
        index = load_index()
        if index is None:
            return
        
        download_by_id(index, translation_id)
    else:
        # Interactive mode
        index = load_index()
        if index is None:
            return
        
        interactive_search_and_download(index)

if __name__ == '__main__':
    main()