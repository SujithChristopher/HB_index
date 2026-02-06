#!/usr/bin/env python3
"""
Bible Translations Index Updater

This script provides easy utilities to maintain and update the Bible translations index.
"""

import os
import subprocess
import json
from datetime import datetime

def update_submodule():
    """Update the Holy-Bible-XML-Format submodule to get latest translations."""
    print("Updating Holy-Bible-XML-Format submodule...")
    try:
        result = subprocess.run(['git', 'submodule', 'update', '--remote', 'Holy-Bible-XML-Format'], 
                              capture_output=True, text=True, check=True)
        print("✓ Submodule updated successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to update submodule: {e}")
        return False

def regenerate_index():
    """Regenerate the Bible translations index."""
    print("Regenerating Bible translations index...")
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        generate_script = os.path.join(script_dir, 'generate_index.py')
        result = subprocess.run(['python', generate_script],
                              capture_output=True, text=True, check=True)
        print("✓ Index regenerated successfully")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to regenerate index: {e}")
        print(e.stderr)
        return False

def show_stats():
    """Show current statistics from the index."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    index_file = os.path.join(project_dir, 'database', 'metadata', 'bible-translations-index.json')
    if not os.path.exists(index_file):
        print("Index file not found. Run regenerate_index() first.")
        return

    with open(index_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    summary = data['summary']
    print("\nCurrent Index Statistics:")
    print("=" * 30)
    print(f"Languages:        {summary['total_languages']}")
    print(f"Total translations: {summary['total_translations']}")
    print(f"Complete Bibles:   {summary['complete_bibles']}")
    print(f"New Testament only: {summary['new_testament_only']}")
    print(f"Old Testament only: {summary['old_testament_only']}")
    
    # Show modification time
    mod_time = datetime.fromtimestamp(os.path.getmtime(index_file))
    print(f"Last updated:      {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")

def search_translations(query):
    """Search for translations by name or language."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    index_file = os.path.join(project_dir, 'database', 'metadata', 'bible-translations-index.json')
    if not os.path.exists(index_file):
        print("Index file not found.")
        return

    with open(index_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    query_lower = query.lower()
    results = []
    
    for lang in data['languages']:
        # Check if language name matches
        if query_lower in lang['language'].lower() or query_lower in lang['native_name'].lower():
            for trans in lang['translations']:
                results.append((lang['language'], trans))
        else:
            # Check translation names
            for trans in lang['translations']:
                if query_lower in trans['name'].lower():
                    results.append((lang['language'], trans))
    
    if results:
        print(f"\nFound {len(results)} results for '{query}':")
        print("=" * 50)
        for lang_name, trans in results[:10]:  # Show first 10 results
            coverage = []
            if trans['testament_coverage']['old_testament']:
                coverage.append('OT')
            if trans['testament_coverage']['new_testament']:
                coverage.append('NT')
            coverage_str = '+'.join(coverage) if coverage else 'None'
            
            print(f"{lang_name:<15} {trans['name']:<40} [{coverage_str}]")
        
        if len(results) > 10:
            print(f"... and {len(results) - 10} more results")
    else:
        print(f"No results found for '{query}'")

def full_update():
    """Perform a complete update: submodule + regenerate index."""
    print("Performing full update...")
    print("1/2 Updating submodule...")
    if not update_submodule():
        return False
    
    print("\n2/2 Regenerating index...")
    if not regenerate_index():
        return False
    
    print("\n✓ Full update completed successfully!")
    show_stats()
    return True

def main():
    """Interactive main function."""
    print("Bible Translations Index Updater")
    print("=" * 40)
    print("Commands:")
    print("  1. update     - Update submodule and regenerate index")
    print("  2. generate   - Regenerate index only")
    print("  3. stats      - Show current statistics")
    print("  4. search     - Search translations")
    print("  5. quit       - Exit")
    
    while True:
        try:
            command = input("\n> ").strip().lower()
            
            if command in ['1', 'update']:
                full_update()
            elif command in ['2', 'generate']:
                regenerate_index()
            elif command in ['3', 'stats']:
                show_stats()
            elif command in ['4', 'search']:
                query = input("Enter search term: ").strip()
                if query:
                    search_translations(query)
            elif command in ['5', 'quit', 'exit', 'q']:
                break
            else:
                print("Unknown command. Please try again.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    main()