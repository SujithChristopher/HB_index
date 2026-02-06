#!/usr/bin/env python3
"""
Find XML files with copyright notices in the Holy Bible XML format repository.
Searches for copyright-related patterns in XML content and metadata.
Uses parallel processing for fast analysis of 1000+ files.
"""

import os
import re
import json
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import defaultdict

# Get project root
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent

# Path to XML files
xml_dir = project_root / "Holy-Bible-XML-Format"

# Copyright patterns to search for
COPYRIGHT_PATTERNS = [
    r'©',  # Copyright symbol
    r'\bcopyright\b',  # "copyright" word
    r'\bcopyrighted\b',  # "copyrighted" word
    r'\(c\)',  # (c) symbol
    r'\b(CC\s*BY|CC0|Public Domain)\b',  # License types
    r'\bcopyright\s+(?:©|\(c\)|notice)',  # More explicit patterns
    r'all\s+rights\s+reserved',  # Rights statement
]

# Compile regex patterns (case-insensitive)
compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in COPYRIGHT_PATTERNS]


def find_copyright_in_file(file_path):
    """
    Search for copyright notices in an XML file.
    Returns: (file_name, has_copyright, matches)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        matches = []
        for pattern in compiled_patterns:
            for match in pattern.finditer(content):
                # Get context around match (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                snippet = content[start:end].replace('\n', ' ').strip()
                matches.append({
                    'pattern': pattern.pattern,
                    'match': match.group(),
                    'snippet': snippet
                })

        has_copyright = len(matches) > 0
        return file_path.name, has_copyright, matches

    except Exception as e:
        return file_path.name, None, f"Error reading file: {e}"


def main():
    """Find all XML files with copyright notices using parallel processing."""

    if not xml_dir.exists():
        print(f"[ERROR] XML directory not found at {xml_dir}")
        return

    # Find all XML files
    xml_files = sorted(xml_dir.glob("*.xml"))

    if not xml_files:
        print(f"[ERROR] No XML files found in {xml_dir}")
        return

    print(f"[START] Analyzing {len(xml_files)} XML files for copyright notices")
    print(f"[INFO] Using parallel processing...\n")

    results = {
        'with_copyright': [],
        'without_copyright': [],
        'errors': []
    }

    # Use ProcessPoolExecutor for parallel processing
    processed = 0
    max_workers = min(8, os.cpu_count() or 4)

    print(f"[INFO] Using {max_workers} worker processes")
    print(f"[PROGRESS] Starting analysis...")
    print()

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all files for processing
        future_to_file = {
            executor.submit(find_copyright_in_file, xml_file): xml_file
            for xml_file in xml_files
        }

        # Process completed tasks
        for future in as_completed(future_to_file):
            file_name, has_copyright, matches = future.result()
            processed += 1

            # Progress indicator every 50 files
            if processed % 50 == 0:
                pct = (processed / len(xml_files)) * 100
                print(f"[PROGRESS] {processed}/{len(xml_files)} files ({pct:.1f}%) processed")

            # Categorize results
            if has_copyright is None:
                results['errors'].append({'file': file_name, 'error': matches})
                sys.stdout.write(f"\r[ERROR] {file_name}: {matches}")
                sys.stdout.flush()
            elif has_copyright:
                results['with_copyright'].append({
                    'file': file_name,
                    'matches_count': len(matches),
                    'matches': matches
                })
            else:
                results['without_copyright'].append(file_name)

    # Print detailed summary
    print("\n")
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files analyzed: {len(xml_files)}")
    print(f"  - Files WITH copyright notices: {len(results['with_copyright'])}")
    print(f"  - Files WITHOUT copyright notices: {len(results['without_copyright'])}")
    print(f"  - Files with errors: {len(results['errors'])}")
    print()

    # Statistics about copyright matches
    total_matches = sum(item['matches_count'] for item in results['with_copyright'])
    avg_matches = total_matches / len(results['with_copyright']) if results['with_copyright'] else 0
    print(f"Copyright statistics:")
    print(f"  - Total copyright references found: {total_matches}")
    print(f"  - Average per file: {avg_matches:.1f}")
    print()

    # Show files with copyright
    if results['with_copyright']:
        print("=" * 80)
        print(f"FILES WITH COPYRIGHT NOTICES ({len(results['with_copyright'])})")
        print("=" * 80)
        print()

        # Sort by match count (descending)
        sorted_items = sorted(
            results['with_copyright'],
            key=lambda x: x['matches_count'],
            reverse=True
        )

        # Show top 20
        for idx, item in enumerate(sorted_items[:20], 1):
            print(f"{idx:3d}. {item['file']}")
            print(f"     Matches: {item['matches_count']}")

            # Show unique match types
            unique_matches = {}
            for match in item['matches']:
                key = match['match'].lower()
                if key not in unique_matches:
                    unique_matches[key] = match

            for match_type in list(unique_matches.keys())[:2]:
                print(f"     - Found: '{match_type}'")

            if item['matches_count'] > 2:
                print(f"     - ... and {item['matches_count'] - 2} more")
            print()

        if len(results['with_copyright']) > 20:
            print(f"... and {len(results['with_copyright']) - 20} more files with copyright notices")
            print()

    # Save detailed results to JSON
    output_file = project_root / "database" / "metadata" / "copyright_notices.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n[INFO] Saving detailed results to JSON...")

    # Prepare data for JSON (remove regex objects)
    json_results = {
        'summary': {
            'total_files': len(xml_files),
            'files_with_copyright': len(results['with_copyright']),
            'files_without_copyright': len(results['without_copyright']),
            'files_with_errors': len(results['errors']),
            'total_copyright_references': total_matches,
            'average_matches_per_file': round(avg_matches, 2)
        },
        'files_with_copyright': [
            {
                'file': item['file'],
                'matches_count': item['matches_count'],
                'matches': [
                    {
                        'match': m['match'],
                        'snippet': m['snippet']
                    }
                    for m in item['matches']
                ]
            }
            for item in sorted(results['with_copyright'], key=lambda x: x['file'])
        ],
        'files_without_copyright': sorted(results['without_copyright'])
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Results saved to: {output_file}")
    print()
    print("=" * 80)


if __name__ == '__main__':
    main()
