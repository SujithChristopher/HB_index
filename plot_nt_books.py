#!/usr/bin/env python3
"""
Plot the distribution of New Testament books across all Bible translations.
This helps identify which translations vary from the standard 27 NT books.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter

def load_index(index_file):
    """Load the Bible translations index."""
    with open(index_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_nt_book_counts(index_data):
    """
    Extract New Testament book counts from all translations.

    For NT-only translations: NT books = total_books
    For complete Bibles: We need to parse the XML to get exact counts
    (for now, we'll note which ones we can't determine precisely)
    """
    nt_counts = []
    translation_details = []

    for language in index_data['languages']:
        for translation in language['translations']:
            coverage = translation['testament_coverage']

            # For NT-only translations, we know the exact NT book count
            if coverage['new_testament'] and not coverage['old_testament']:
                nt_book_count = coverage['total_books']
                nt_counts.append(nt_book_count)
                translation_details.append({
                    'language': language['language'],
                    'name': translation['name'],
                    'nt_books': nt_book_count,
                    'type': 'NT-only'
                })

            # For complete Bibles, we need more detailed data
            # Standard full Bible has 39 OT + 27 NT = 66 books
            # But variations exist (e.g., Catholic Bibles with deuterocanonical books)
            elif coverage['new_testament'] and coverage['old_testament']:
                total = coverage['total_books']
                # Standard assumption: 27 NT books for standard 66-book Bible
                # For 73-book Catholic Bible: typically still 27 NT books
                # For other totals: estimate based on patterns

                if total == 66:
                    # Standard Protestant Bible: 39 OT + 27 NT
                    estimated_nt = 27
                elif total == 73:
                    # Catholic Bible with Deuterocanonical: 46 OT + 27 NT
                    estimated_nt = 27
                elif total > 66:
                    # Likely has extra OT books, NT probably standard 27
                    estimated_nt = 27
                elif total < 66 and total > 27:
                    # Missing some books, assume proportional split or 27 NT
                    # More conservative: assume NT is complete, OT is incomplete
                    estimated_nt = min(27, total - 20)  # Assuming at least 20 OT books
                else:
                    estimated_nt = 27  # Default assumption

                nt_counts.append(estimated_nt)
                translation_details.append({
                    'language': language['language'],
                    'name': translation['name'],
                    'nt_books': estimated_nt,
                    'total_books': total,
                    'type': 'Complete Bible (estimated)'
                })

    return nt_counts, translation_details

def create_visualization(nt_counts, translation_details):
    """Create a comprehensive visualization of NT book distribution."""

    # Count the distribution
    count_distribution = Counter(nt_counts)

    # Create figure with multiple subplots
    fig = plt.figure(figsize=(16, 10))

    # Subplot 1: Histogram of NT book counts
    ax1 = plt.subplot(2, 2, 1)
    counts_sorted = sorted(count_distribution.items())
    books = [x[0] for x in counts_sorted]
    frequencies = [x[1] for x in counts_sorted]

    colors = ['#e74c3c' if count != 27 else '#2ecc71' for count in books]
    bars = ax1.bar(books, frequencies, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Number of New Testament Books', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Translations', fontsize=12, fontweight='bold')
    ax1.set_title('Distribution of NT Books Across All Translations', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Subplot 2: Pie chart of standard vs. non-standard
    ax2 = plt.subplot(2, 2, 2)
    standard_count = count_distribution.get(27, 0)
    non_standard_count = sum(frequencies) - standard_count

    pie_data = [standard_count, non_standard_count]
    pie_labels = [f'Standard (27 books)\n{standard_count} translations',
                  f'Non-standard\n{non_standard_count} translations']
    pie_colors = ['#2ecc71', '#e74c3c']

    wedges, texts, autotexts = ax2.pie(pie_data, labels=pie_labels, colors=pie_colors,
                                        autopct='%1.1f%%', startangle=90,
                                        textprops={'fontsize': 10, 'fontweight': 'bold'})
    ax2.set_title('Standard vs. Non-standard NT Book Counts', fontsize=14, fontweight='bold')

    # Subplot 3: Statistics table
    ax3 = plt.subplot(2, 2, 3)
    ax3.axis('off')

    stats_text = f"""
    Statistics Summary:

    Total Translations Analyzed: {len(nt_counts)}

    Most Common NT Book Count: {max(count_distribution, key=count_distribution.get)}
    Standard (27 books): {standard_count} ({100*standard_count/len(nt_counts):.1f}%)

    Range: {min(nt_counts)} - {max(nt_counts)} books
    Mean: {np.mean(nt_counts):.2f} books
    Median: {np.median(nt_counts):.0f} books

    Unique NT Book Counts: {len(count_distribution)}

    Breakdown by Type:
    - NT-only: {sum(1 for d in translation_details if d['type'] == 'NT-only')}
    - Complete Bible: {sum(1 for d in translation_details if d['type'] == 'Complete Bible (estimated)')}
    """

    ax3.text(0.1, 0.5, stats_text, fontsize=11, family='monospace',
             verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Subplot 4: Top variations from standard
    ax4 = plt.subplot(2, 2, 4)
    ax4.axis('off')

    # Find non-standard translations
    non_standard = [d for d in translation_details if d['nt_books'] != 27]
    non_standard_sorted = sorted(non_standard, key=lambda x: abs(x['nt_books'] - 27), reverse=True)

    variations_text = "Top Variations from Standard (27 books):\n\n"
    for i, trans in enumerate(non_standard_sorted[:15], 1):
        diff = trans['nt_books'] - 27
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        name = trans['name'][:40] + '...' if len(trans['name']) > 40 else trans['name']
        variations_text += f"{i:2d}. {name}\n"
        variations_text += f"    {trans['language']}: {trans['nt_books']} books ({diff_str})\n"

    if len(non_standard) == 0:
        variations_text += "All translations have standard 27 NT books!"

    ax4.text(0.05, 0.95, variations_text, fontsize=8, family='monospace',
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    plt.tight_layout()
    return fig

def print_detailed_analysis(nt_counts, translation_details):
    """Print detailed analysis to console."""
    print("\n" + "="*80)
    print("NEW TESTAMENT BOOKS DISTRIBUTION ANALYSIS")
    print("="*80)

    count_dist = Counter(nt_counts)

    print(f"\nTotal translations analyzed: {len(nt_counts)}")
    print(f"\nDistribution of NT book counts:")
    for count, freq in sorted(count_dist.items()):
        percentage = 100 * freq / len(nt_counts)
        bar = '█' * int(percentage / 2)
        standard_marker = ' ← STANDARD' if count == 27 else ''
        print(f"  {count:2d} books: {freq:4d} translations ({percentage:5.1f}%) {bar}{standard_marker}")

    # List some examples of non-standard translations
    non_standard = [d for d in translation_details if d['nt_books'] != 27]
    if non_standard:
        print(f"\n{len(non_standard)} translations with non-standard NT book counts:")
        print("\nExamples:")
        for trans in sorted(non_standard, key=lambda x: x['nt_books'])[:10]:
            print(f"  - {trans['language']}: {trans['name']}")
            print(f"    NT books: {trans['nt_books']}, Type: {trans['type']}")
    else:
        print("\nAll translations have the standard 27 NT books!")

def main():
    """Main function."""
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_file = os.path.join(script_dir, 'bible-translations-index.json')
    output_file = os.path.join(script_dir, 'nt_books_distribution.png')

    print("Loading Bible translations index...")
    index_data = load_index(index_file)

    print("Extracting NT book counts...")
    nt_counts, translation_details = extract_nt_book_counts(index_data)

    print("Creating visualization...")
    fig = create_visualization(nt_counts, translation_details)

    # Save the plot
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {output_file}")

    # Print detailed analysis
    print_detailed_analysis(nt_counts, translation_details)

    # Show the plot
    print("\nDisplaying plot...")
    plt.show()

if __name__ == '__main__':
    main()
