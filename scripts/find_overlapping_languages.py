import json
import os
from thefuzz import fuzz

def find_overlapping_languages(index_file=None):
    if index_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        index_file = os.path.join(project_dir, 'database', 'metadata', 'bible-translations-index.json')
    """
    Finds potential overlapping languages in the Bible translations index.
    """
    with open(index_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    languages = [lang['language'] for lang in data['languages']]
    languages.sort()

    overlaps = {}

    for i, lang1 in enumerate(languages):
        for lang2 in languages[i+1:]:
            if fuzz.ratio(lang1, lang2) > 80:
                if lang1 not in overlaps:
                    overlaps[lang1] = []
                if lang2 not in overlaps[lang1]:
                    overlaps[lang1].append(lang2)

    if overlaps:
        print("Potential overlapping languages found:")
        for lang, related in overlaps.items():
            print(f"- {lang}: {', '.join(related)}")
    else:
        print("No overlapping languages found.")

if __name__ == '__main__':
    find_overlapping_languages()
