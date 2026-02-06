#!/usr/bin/env python3
"""
Update bible-translations-index.json to add classification field:
- protestant: boolean - true ONLY if translation perfectly matches Protestant canon
  (66 books with both OT and NT correctly marked as true)
"""

import json
import os

def update_index_with_classifications(index_file=None):
    if index_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        index_file = os.path.join(project_dir, 'database', 'metadata', 'bible-translations-index.json')
    """Update the index file with protestant classification field."""

    # Load the current index
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)

    total_translations = 0
    protestant_count = 0
    misclassified_count = 0

    # Update each translation
    for language in index['languages']:
        for translation in language['translations']:
            total_translations += 1
            total_books = translation['testament_coverage']['total_books']
            has_ot = translation['testament_coverage']['old_testament']
            has_nt = translation['testament_coverage']['new_testament']

            # Mark as protestant ONLY if it perfectly matches:
            # - 66 books (39 OT + 27 NT)
            # - Both testaments correctly marked as true
            translation['protestant'] = (
                total_books == 66 and
                has_ot == True and
                has_nt == True
            )

            if translation['protestant']:
                protestant_count += 1

            # Count misclassified (66 books but wrong testament flags)
            if total_books == 66 and not translation['protestant']:
                misclassified_count += 1

    # Update summary with new statistics
    index['summary']['protestant_canon'] = protestant_count

    # Save the updated index
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    return {
        'total': total_translations,
        'misclassified': misclassified_count,
        'protestant': protestant_count
    }

def print_updated_translations(index_file):
    """Print details of translations with 66 books that aren't marked as protestant."""
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)

    print("\n" + "="*80)
    print("MISCLASSIFIED TRANSLATIONS (66 books but protestant=false)")
    print("="*80)

    count = 0
    for language in index['languages']:
        for translation in language['translations']:
            total_books = translation['testament_coverage']['total_books']
            is_protestant = translation.get('protestant', False)

            # Show translations with 66 books but not marked as protestant
            if total_books == 66 and not is_protestant:
                count += 1
                print(f"\nFile: {translation['filename']}")
                print(f"Language: {language['language']}")
                print(f"Name: {translation['name']}")
                print(f"Total books: {total_books}")
                print(f"Protestant: {is_protestant}")
                print(f"Testament coverage: OT={translation['testament_coverage']['old_testament']}, "
                      f"NT={translation['testament_coverage']['new_testament']}")

    if count == 0:
        print("\n✓ No misclassifications found - all 66-book translations correctly marked!")

def main():
    """Main function."""
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_file = os.path.join(script_dir, 'bible-translations-index.json')

    print("Updating Bible translations index with classification fields...")
    print(f"Index file: {index_file}")

    # Update the index
    stats = update_index_with_classifications(index_file)

    print(f"\n✓ Index updated successfully!")
    print(f"\nStatistics:")
    print(f"  Total translations: {stats['total']}")
    print(f"  Misclassified: {stats['misclassified']}")
    print(f"  Protestant canon (66 books): {stats['protestant']}")

    # Print details of misclassified translations
    print_updated_translations(index_file)

    print("\n" + "="*80)
    print("Index file has been updated with:")
    print("  'protestant' field (boolean) - true ONLY if perfectly matches:")
    print("    - 66 books (39 OT + 27 NT)")
    print("    - Both old_testament and new_testament marked as true")
    print("  This ensures misclassified translations are marked as protestant=false")
    print("="*80)

if __name__ == '__main__':
    main()
