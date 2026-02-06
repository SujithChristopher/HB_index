#!/usr/bin/env python3
"""
Plot the distribution of Old Testament books across all Bible translations.
This helps identify which translations vary from the standard 39 OT books.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter

def load_index(index_file):
    """Load the Bible translations index."""
    with open(index_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_ot_book_counts(index_data):
    """
    Extract Old Testament book counts from all translations.

    Standard counts:
    - Protestant: 39 OT books
    - Catholic: 46 OT books (includes Deuterocanonical)
    - Orthodox: 49-51 OT books (includes additional books)
    """
    ot_counts = []
    translation_details = []

    for language in index_data['languages']:
        for translation in language['translations']:
            coverage = translation['testament_coverage']

            # Skip NT-only translations
            if not coverage['old_testament']:
                continue

            # For OT-only translations
            if coverage['old_testament'] and not coverage['new_testament']:
                ot_book_count = coverage['total_books']
                ot_counts.append(ot_book_count)
                translation_details.append({
                    'language': language['language'],
                    'name': translation['name'],
                    'filename': translation['filename'],
                    'ot_books': ot_book_count,
                    'total_books': ot_book_count,
                    'type': 'OT-only'
                })

            # For complete Bibles, estimate OT books
            elif coverage['new_testament'] and coverage['old_testament']:
                total = coverage['total_books']

                # Standard patterns:
                # 66 books = 39 OT + 27 NT (Protestant)
                # 73 books = 46 OT + 27 NT (Catholic)
                # 76-78 books = 49-51 OT + 27 NT (Orthodox)

                if total == 66:
                    estimated_ot = 39  # Protestant
                elif total == 73:
                    estimated_ot = 46  # Catholic
                elif total >= 76 and total <= 78:
                    estimated_ot = total - 27  # Orthodox
                elif total > 78:
                    # Likely has additional OT books
                    estimated_ot = total - 27
                elif total > 27:
                    # Assume standard NT (27), rest is OT
                    estimated_ot = total - 27
                else:
                    estimated_ot = 0  # Should not happen for complete Bibles

                if estimated_ot > 0:
                    ot_counts.append(estimated_ot)
                    translation_details.append({
                        'language': language['language'],
                        'name': translation['name'],
                        'filename': translation['filename'],
                        'ot_books': estimated_ot,
                        'total_books': total,
                        'type': 'Complete Bible (estimated)'
                    })

    return ot_counts, translation_details

def categorize_ot_count(count):
    """Categorize OT book count by tradition."""
    if count == 39:
        return 'Protestant (39)'
    elif count == 46:
        return 'Catholic (46)'
    elif count >= 49 and count <= 51:
        return f'Orthodox ({count})'
    elif count < 39:
        return f'Incomplete ({count})'
    elif count > 51:
        return f'Extended ({count})'
    else:
        return f'Other ({count})'

def create_visualization(ot_counts, translation_details):
    """Create a comprehensive visualization of OT book distribution."""

    # Count the distribution
    count_distribution = Counter(ot_counts)

    # Create figure with multiple subplots
    fig = plt.figure(figsize=(16, 10))

    # Subplot 1: Histogram of OT book counts
    ax1 = plt.subplot(2, 2, 1)
    counts_sorted = sorted(count_distribution.items())
    books = [x[0] for x in counts_sorted]
    frequencies = [x[1] for x in counts_sorted]

    # Color code: green for standard Protestant (39), blue for Catholic (46),
    # orange for Orthodox (49-51), red for others
    def get_color(count):
        if count == 39:
            return '#2ecc71'  # Green - Protestant
        elif count == 46:
            return '#3498db'  # Blue - Catholic
        elif 49 <= count <= 51:
            return '#f39c12'  # Orange - Orthodox
        else:
            return '#e74c3c'  # Red - Non-standard

    colors = [get_color(count) for count in books]
    bars = ax1.bar(books, frequencies, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Number of Old Testament Books', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Translations', fontsize=12, fontweight='bold')
    ax1.set_title('Distribution of OT Books Across All Translations', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Subplot 2: Pie chart by tradition
    ax2 = plt.subplot(2, 2, 2)
    protestant_count = count_distribution.get(39, 0)
    catholic_count = count_distribution.get(46, 0)
    orthodox_count = sum(count_distribution.get(i, 0) for i in range(49, 52))
    other_count = sum(frequencies) - protestant_count - catholic_count - orthodox_count

    pie_data = []
    pie_labels = []
    pie_colors = []

    if protestant_count > 0:
        pie_data.append(protestant_count)
        pie_labels.append(f'Protestant (39)\n{protestant_count} translations')
        pie_colors.append('#2ecc71')

    if catholic_count > 0:
        pie_data.append(catholic_count)
        pie_labels.append(f'Catholic (46)\n{catholic_count} translations')
        pie_colors.append('#3498db')

    if orthodox_count > 0:
        pie_data.append(orthodox_count)
        pie_labels.append(f'Orthodox (49-51)\n{orthodox_count} translations')
        pie_colors.append('#f39c12')

    if other_count > 0:
        pie_data.append(other_count)
        pie_labels.append(f'Other\n{other_count} translations')
        pie_colors.append('#e74c3c')

    wedges, texts, autotexts = ax2.pie(pie_data, labels=pie_labels, colors=pie_colors,
                                        autopct='%1.1f%%', startangle=90,
                                        textprops={'fontsize': 10, 'fontweight': 'bold'})
    ax2.set_title('OT Book Counts by Tradition', fontsize=14, fontweight='bold')

    # Subplot 3: Statistics table
    ax3 = plt.subplot(2, 2, 3)
    ax3.axis('off')

    stats_text = f"""
    Statistics Summary:

    Total Translations Analyzed: {len(ot_counts)}

    Distribution by Tradition:
    - Protestant (39 books): {protestant_count} ({100*protestant_count/len(ot_counts) if len(ot_counts) > 0 else 0:.1f}%)
    - Catholic (46 books): {catholic_count} ({100*catholic_count/len(ot_counts) if len(ot_counts) > 0 else 0:.1f}%)
    - Orthodox (49-51): {orthodox_count} ({100*orthodox_count/len(ot_counts) if len(ot_counts) > 0 else 0:.1f}%)
    - Other variations: {other_count} ({100*other_count/len(ot_counts) if len(ot_counts) > 0 else 0:.1f}%)

    Range: {min(ot_counts) if ot_counts else 0} - {max(ot_counts) if ot_counts else 0} books
    Mean: {np.mean(ot_counts) if ot_counts else 0:.2f} books
    Median: {np.median(ot_counts) if ot_counts else 0:.0f} books

    Unique OT Book Counts: {len(count_distribution)}

    Breakdown by Type:
    - OT-only: {sum(1 for d in translation_details if d['type'] == 'OT-only')}
    - Complete Bible: {sum(1 for d in translation_details if d['type'] == 'Complete Bible (estimated)')}
    """

    ax3.text(0.1, 0.5, stats_text, fontsize=10, family='monospace',
             verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Subplot 4: Non-standard variations
    ax4 = plt.subplot(2, 2, 4)
    ax4.axis('off')

    # Find non-standard translations (not 39, 46, or 49-51)
    standard_counts = {39, 46, 49, 50, 51}
    non_standard = [d for d in translation_details if d['ot_books'] not in standard_counts]
    non_standard_sorted = sorted(non_standard, key=lambda x: abs(x['ot_books'] - 39), reverse=True)

    variations_text = "Non-Standard OT Book Counts:\n\n"
    for i, trans in enumerate(non_standard_sorted[:20], 1):
        name = trans['name'][:35] + '...' if len(trans['name']) > 35 else trans['name']
        variations_text += f"{i:2d}. {name}\n"
        variations_text += f"    {trans['language']}: {trans['ot_books']} books\n"
        variations_text += f"    File: {trans['filename'][:40]}\n"

    if len(non_standard) == 0:
        variations_text += "All translations follow standard\ncanon patterns!"

    ax4.text(0.05, 0.95, variations_text, fontsize=7.5, family='monospace',
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    plt.tight_layout()
    return fig

def print_detailed_analysis(ot_counts, translation_details):
    """Print detailed analysis to console."""
    print("\n" + "="*80)
    print("OLD TESTAMENT BOOKS DISTRIBUTION ANALYSIS")
    print("="*80)

    count_dist = Counter(ot_counts)

    print(f"\nTotal translations analyzed: {len(ot_counts)}")
    print(f"\nDistribution of OT book counts:")
    for count, freq in sorted(count_dist.items()):
        percentage = 100 * freq / len(ot_counts)
        bar = '█' * int(percentage / 2)
        category = categorize_ot_count(count)
        print(f"  {count:2d} books: {freq:4d} translations ({percentage:5.1f}%) {bar} {category}")

    # List non-standard translations
    standard_counts = {39, 46, 49, 50, 51}
    non_standard = [d for d in translation_details if d['ot_books'] not in standard_counts]

    print(f"\n{len(non_standard)} translations with non-standard OT book counts:")
    print("\nFiles with discrepancies:")
    print("-" * 80)

    # Group by book count
    by_count = {}
    for trans in non_standard:
        count = trans['ot_books']
        if count not in by_count:
            by_count[count] = []
        by_count[count].append(trans)

    for count in sorted(by_count.keys()):
        trans_list = by_count[count]
        print(f"\n{count} OT Books ({len(trans_list)} translations):")
        for trans in sorted(trans_list, key=lambda x: x['filename']):
            print(f"  - {trans['filename']}")
            print(f"    Language: {trans['language']}")
            print(f"    Name: {trans['name']}")
            print(f"    Type: {trans['type']}")

def save_discrepancies_report(translation_details, output_file):
    """Save a detailed report of discrepancies to a text file."""
    standard_counts = {39, 46, 49, 50, 51}
    non_standard = [d for d in translation_details if d['ot_books'] not in standard_counts]

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("OLD TESTAMENT BOOKS DISCREPANCIES REPORT\n")
        f.write("="*80 + "\n\n")

        f.write(f"Total translations with OT books: {len(translation_details)}\n")
        f.write(f"Non-standard translations: {len(non_standard)}\n\n")

        # Group by book count
        by_count = {}
        for trans in non_standard:
            count = trans['ot_books']
            if count not in by_count:
                by_count[count] = []
            by_count[count].append(trans)

        for count in sorted(by_count.keys()):
            trans_list = by_count[count]
            f.write(f"\n{'='*80}\n")
            f.write(f"{count} OT BOOKS ({len(trans_list)} translations)\n")
            f.write(f"{'='*80}\n\n")

            for trans in sorted(trans_list, key=lambda x: x['filename']):
                f.write(f"Filename: {trans['filename']}\n")
                f.write(f"Language: {trans['language']}\n")
                f.write(f"Name: {trans['name']}\n")
                f.write(f"OT Books: {trans['ot_books']}\n")
                f.write(f"Total Books: {trans['total_books']}\n")
                f.write(f"Type: {trans['type']}\n")
                f.write("-" * 80 + "\n\n")

    print(f"\nDetailed discrepancies report saved to: {output_file}")

def main():
    """Main function."""
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_file = os.path.join(script_dir, 'bible-translations-index.json')
    output_file = os.path.join(script_dir, 'ot_books_distribution.png')
    report_file = os.path.join(script_dir, 'ot_books_discrepancies.txt')

    print("Loading Bible translations index...")
    index_data = load_index(index_file)

    print("Extracting OT book counts...")
    ot_counts, translation_details = extract_ot_book_counts(index_data)

    print("Creating visualization...")
    fig = create_visualization(ot_counts, translation_details)

    # Save the plot
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {output_file}")

    # Print detailed analysis
    print_detailed_analysis(ot_counts, translation_details)

    # Save discrepancies report
    save_discrepancies_report(translation_details, report_file)

    # Show the plot
    print("\nDisplaying plot...")
    plt.show()

if __name__ == '__main__':
    main()
