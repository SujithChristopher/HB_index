# Pull Request: Add Native Bible Book Names for Multilingual Support

## Summary
This PR adds native Bible book names for 16 major languages to enhance multilingual support for the Bible app.

## What's Included

### New Files
- **bible-book-names.json** - Main data file with native book names for all 66 canonical Protestant Bible books across 16 languages
- **bible-book-names-template.json** - Template structure for the JSON file
- **generate_book_names_json.py** - Script to generate the JSON file programmatically
- **collect_book_names.py** - Utility for managing and adding book names for new languages
- **extract_languages.py** - Helper script to extract languages from the translations index

### Languages Covered (16 total)
1. English (English) - en
2. Spanish (Español) - es
3. French (Français) - fr
4. German (Deutsch) - de
5. Portuguese (Português) - pt
6. Russian (Русский) - ru
7. Greek (Ελληνικά) - el
8. Arabic (العربية) - ar
9. Chinese (中文) - zh
10. Japanese (日本語) - ja
11. Korean (한국어) - ko
12. Hindi (हिन्दी) - hi
13. Tamil (தமிழ்) - ta
14. Telugu (తెలుగు) - te
15. Bengali (বাংলা) - bn
16. Malayalam (മലയാളം) - ml

## Coverage
- ✅ All 66 books (39 Old Testament + 27 New Testament)
- ✅ Native scripts for all languages (Latin, Cyrillic, Greek, Arabic, CJK, Indic scripts)
- ✅ Consistent structure across all languages
- ✅ Complete metadata and documentation

## Research Methodology
Book names were collected through comprehensive web research using official Bible society websites, Wikipedia, language-specific Bible resources, and translation comparison documents.

## Benefits
1. Better User Experience - Users can see book names in their native language
2. Multilingual Support - Supports major world languages and scripts
3. Extensible - Easy to add more languages using provided scripts
4. API Ready - JSON format integrates seamlessly with the Bible app
5. Cultural Accuracy - Uses authentic native names from established translations

## Future Work
The structure is designed to be extensible. Additional languages from the bible-translations-index.json can be added incrementally using the provided utility scripts.

Branch: claude/add-native-book-names-011CV3sX7R3jkXARpGpeEkxT
