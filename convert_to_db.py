import os
import sqlcipher3 as sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

def get_encryption_key():
    """Load the encryption key from .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        raise FileNotFoundError(".env file not found. Ensure ENCRYPTION_KEY is set.")
    
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("ENCRYPTION_KEY="):
                return line.strip().split("=")[1]
    
    raise ValueError("ENCRYPTION_KEY not found in .env file.")

def convert_xml_to_db(xml_path, db_path, encryption_key):
    print(f"Converting {xml_path} to {db_path}...")
    
    # Delete existing DB if it exists to ensure a fresh encrypted creation
    if db_path.exists():
        db_path.unlink()
    
    # Parse XML
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    translation_name = root.attrib.get('translation', 'Unknown')
    status = root.attrib.get('status', 'Unknown')
    
    # Connect to SQLite (with SQLCipher support)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Apply encryption key
    cursor.execute(f"PRAGMA key = '{encryption_key}'")
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            testament TEXT,
            book_number INTEGER,
            chapter_number INTEGER,
            verse_number INTEGER,
            text TEXT
        )
    ''')
    
    # Clear existing data if any
    cursor.execute('DELETE FROM metadata')
    cursor.execute('DELETE FROM verses')
    
    # Insert metadata
    cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)', ('translation', translation_name))
    cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)', ('status', status))
    
    # Insert verses
    verses_to_insert = []
    
    # Try finding testament elements first to preserve testament names if they exist
    testaments = root.findall('testament')
    if testaments:
        for testament in testaments:
            testament_name = testament.attrib.get('name')
            for book in testament.findall('book'):
                book_num = int(book.attrib.get('number'))
                for chapter in book.findall('chapter'):
                    chapter_num = int(chapter.attrib.get('number'))
                    for verse in chapter.findall('verse'):
                        verse_num = int(verse.attrib.get('number'))
                        verse_text = verse.text or ""
                        verses_to_insert.append((
                            testament_name,
                            book_num,
                            chapter_num,
                            verse_num,
                            verse_text
                        ))
    else:
        # Fallback for XMLs without <testament> tags
        for book in root.findall('book'):
            book_num = int(book.attrib.get('number'))
            # We can guess testament based on book number if needed, 
            # but let's keep it None/empty if not provided.
            # Usually 1-39 is OT, 40-66 is NT in standard Protestant Bibles.
            testament_name = "Old" if book_num <= 39 else "New"
            for chapter in book.findall('chapter'):
                chapter_num = int(chapter.attrib.get('number'))
                for verse in chapter.findall('verse'):
                    verse_num = int(verse.attrib.get('number'))
                    verse_text = verse.text or ""
                    verses_to_insert.append((
                        testament_name,
                        book_num,
                        chapter_num,
                        verse_num,
                        verse_text
                    ))
    
    cursor.executemany('''
        INSERT INTO verses (testament, book_number, chapter_number, verse_number, text)
        VALUES (?, ?, ?, ?, ?)
    ''', verses_to_insert)
    
    conn.commit()
    conn.close()
    print(f"Successfully converted {len(verses_to_insert)} verses.")

if __name__ == "__main__":
    try:
        encryption_key = get_encryption_key()
    except Exception as e:
        print(f"Error loading encryption key: {e}")
        exit(1)

    xml_dir = Path("Holy-Bible-XML-Format")
    db_dir = Path("database")
    
    if not db_dir.exists():
        db_dir.mkdir()
        
    xml_files = list(xml_dir.glob("*.xml"))
    print(f"Found {len(xml_files)} XML files.")
    
    for xml_file in xml_files:
        db_file = db_dir / f"{xml_file.stem}.db"
        try:
            convert_xml_to_db(xml_file, db_file, encryption_key)
        except Exception as e:
            print(f"Failed to convert {xml_file}: {e}")
