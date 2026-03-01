import os
import sqlcipher3 as sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import base64

def get_encryption_key():
    """Load the encryption key from .env file."""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    env_path = project_dir / ".env"
    if not env_path.exists():
        raise FileNotFoundError(".env file not found. Ensure ENCRYPTION_KEY is set.")
    
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("ENCRYPTION_KEY="):
                return line.strip().split("ENCRYPTION_KEY=")[1]
    
    raise ValueError("ENCRYPTION_KEY not found in .env file.")

def convert_xml_to_db(xml_path, db_path, encryption_key):
    # Parse XML first (outside of connection for better error isolation)
    tree = ET.parse(xml_path)
    root = tree.getroot()

    translation_name = root.attrib.get('translation', 'Unknown')
    # Derive translation_id from filename, removing "bible" suffix if present
    # e.g., "AcehBible.xml" -> "aceh", "KJV.xml" -> "kjv"
    translation_id = xml_path.stem.lower()
    if translation_id.endswith('bible'):
        translation_id = translation_id[:-5]  # Remove "bible" suffix
    status = root.attrib.get('status', 'Unknown')
    
    # Delete existing DB if it exists
    if db_path.exists():
        db_path.unlink()
    
    # Connect and Apply encryption
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Use hex key format with x'...' syntax for SQLCipher
    cursor.execute(f"PRAGMA key = \"x'{encryption_key}'\"")

    # Set SQLCipher 4.x compatibility settings (must match Rust side)
    cursor.execute("PRAGMA cipher_page_size = 4096")
    cursor.execute("PRAGMA kdf_iter = 256000")
    cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
    cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")

    # Create tables (matching Rust schema exactly)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS translations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            language TEXT NOT NULL,
            language_name TEXT,
            description TEXT,
            download_url TEXT,
            legal_notice TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            translation_id TEXT NOT NULL,
            id INTEGER NOT NULL,
            name TEXT NOT NULL,
            abbreviation TEXT NOT NULL,
            chapter_count INTEGER NOT NULL,
            testament TEXT NOT NULL,
            PRIMARY KEY (translation_id, id),
            FOREIGN KEY (translation_id) REFERENCES translations(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verses (
            translation_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY (translation_id, book_id, chapter, verse),
            FOREIGN KEY (translation_id, book_id) REFERENCES books(translation_id, id) ON DELETE CASCADE
        )
    ''')

    # Insert translation metadata
    cursor.execute('''
        INSERT OR REPLACE INTO translations (id, name, abbreviation, language, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (translation_id, translation_name, translation_id.upper(), 'en', status))
    
    # Process verses and track books
    verses_to_insert = []
    books_map = {}  # book_id -> {name, testament, max_chapter}

    testaments = root.findall('testament')
    if testaments:
        for testament in testaments:
            testament_name = testament.attrib.get('name')
            for book in testament.findall('book'):
                book_num = int(book.attrib.get('number'))
                book_name = book.attrib.get('name', f'Book {book_num}')

                # Track book info
                if book_num not in books_map:
                    books_map[book_num] = {
                        'name': book_name,
                        'testament': testament_name,
                        'max_chapter': 0
                    }

                for chapter in book.findall('chapter'):
                    chapter_num = int(chapter.attrib.get('number'))
                    books_map[book_num]['max_chapter'] = max(books_map[book_num]['max_chapter'], chapter_num)

                    for verse in chapter.findall('verse'):
                        verses_to_insert.append((
                            translation_id, book_num, chapter_num,
                            int(verse.attrib.get('number')), verse.text or ""
                        ))
    else:
        for book in root.findall('book'):
            book_num = int(book.attrib.get('number'))
            book_name = book.attrib.get('name', f'Book {book_num}')
            testament_name = "Old Testament" if book_num <= 39 else "New Testament"

            # Track book info
            if book_num not in books_map:
                books_map[book_num] = {
                    'name': book_name,
                    'testament': testament_name,
                    'max_chapter': 0
                }

            for chapter in book.findall('chapter'):
                chapter_num = int(chapter.attrib.get('number'))
                books_map[book_num]['max_chapter'] = max(books_map[book_num]['max_chapter'], chapter_num)

                for verse in chapter.findall('verse'):
                    verses_to_insert.append((
                        translation_id, book_num, chapter_num,
                        int(verse.attrib.get('number')), verse.text or ""
                    ))

    # Insert books
    books_to_insert = [
        (
            translation_id,
            book_id,
            info['name'],
            info['name'][:3].upper(),  # Simple abbreviation
            info['max_chapter'],
            info['testament']
        )
        for book_id, info in books_map.items()
    ]

    cursor.executemany('''
        INSERT OR REPLACE INTO books (translation_id, id, name, abbreviation, chapter_count, testament)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', books_to_insert)

    # Insert verses with translation_id
    cursor.executemany('''
        INSERT OR REPLACE INTO verses (translation_id, book_id, chapter, verse, text)
        VALUES (?, ?, ?, ?, ?)
    ''', verses_to_insert)
    
    conn.commit()
    conn.close()
    return len(verses_to_insert)

if __name__ == "__main__":
    start_time = time.perf_counter()
    try:
        encryption_key = get_encryption_key()
        print(encryption_key)
        encryption_key = base64.b64decode(encryption_key).hex()
    except Exception as e:
        print(f"Error loading encryption key: {e}")
        exit(1)

    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    xml_dir = project_dir / "Holy-Bible-XML-Format"
    db_dir = project_dir / "database/translations"
    db_dir.mkdir(exist_ok=True)
        
    xml_files = list(xml_dir.glob("*.xml"))
    total_files = len(xml_files)
    print(f"Found {total_files} XML files. Starting parallel conversion...")
    
    completed = 0
    total_verses = 0
    
    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(convert_xml_to_db, xml_file, db_dir / f"{xml_file.stem}.db", encryption_key): xml_file 
            for xml_file in xml_files
        }
        
        for future in as_completed(futures):
            xml_file = futures[future]
            completed += 1
            try:
                verse_count = future.result()
                total_verses += verse_count
                if completed % 50 == 0 or completed == total_files:
                    print(f"Progress: {completed}/{total_files} files converted ({total_verses:,} total verses).")
            except Exception as e:
                print(f"Failed to convert {xml_file.name}: {e}")
    
    end_time = time.perf_counter()
    print(f"\nFinal Summary:")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")
    print(f"Average time per file: {(end_time - start_time) / total_files:.4f} seconds")
    print(f"Total verses processed: {total_verses:,}")
