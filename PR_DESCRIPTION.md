# Pull Request: Add Protestant Canon Classification to Bible Translations Index

## Summary

This PR adds a `protestant` boolean field to the Bible translations index to help apps reliably identify standard Protestant canon translations (66 books with correct testament coverage).

## Changes Made

### 1. Updated `bible-translations-index.json`
- Added `protestant` field to all 1,045 translations
- `protestant = true`: 66 books with both `old_testament=true` and `new_testament=true` (694 translations)
- `protestant = false`: all other translations, including misclassified ones (351 translations)

### 2. Updated `generate_index.py`
- Automatically calculates and adds `protestant` field during index generation
- Added `protestant_canon` count to summary statistics
- Ensures future index regenerations maintain this classification

### 3. Created `update_index_classifications.py`
- Utility script to add `protestant` field to existing index
- Identifies and reports misclassified translations
- Can be run to update the index without full regeneration

## Problem Solved

### Misclassified Translations Identified
4 translations have 66 books but incorrect testament coverage flags:

1. **ChineseTTVHBible.xml** - Marked as NT-only but has 66 books
2. **DutchSVVBible.xml** - Marked as OT-only but has 66 books
3. **HungarianBible.xml** - Marked as OT-only but has 66 books
4. **Portuguese1969Bible.xml** - Marked as OT-only but has 66 books

These are now correctly marked as `protestant=false` to prevent them from affecting apps that filter for standard Protestant Bibles.

## Statistics

- **Total translations**: 1,045
- **Protestant canon (correct)**: 694 (66.4%)
- **Misclassified 66-book translations**: 4 (0.4%)
- **Other translations**: 347 (33.2%)

## Benefits for App Development

When building apps around `bible-translations-index.json`:
- ✅ Reliable filtering for standard Protestant Bibles using `protestant === true`
- ✅ Misclassified translations won't break app logic
- ✅ Clear distinction between complete Bibles and partial translations
- ✅ Future-proof: new translations will automatically get this field

## Testing

All tests pass:
- ✓ Protestant field exists in all translations
- ✓ 4 misclassified translations correctly marked as `protestant=false`
- ✓ Standard 66-book translations correctly marked as `protestant=true`
- ✓ Summary statistics updated correctly
- ✓ 694 + 4 = 698 total 66-book translations (validated)

## Related Analysis

This PR is based on the analysis from the previous branch that identified these discrepancies through statistical analysis of OT and NT book distributions across all translations.

---

**Branch**: `claude/fix-misclassified-translations-011CV3ozoCzkbNDVaM8Az3F2`

**How to create the PR**:
Visit: https://github.com/SujithChristopher/HB_index/pull/new/claude/fix-misclassified-translations-011CV3ozoCzkbNDVaM8Az3F2
