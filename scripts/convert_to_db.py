import os
import sqlcipher3 as sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

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
                return line.strip().split("=")[1]
    
    raise ValueError("ENCRYPTION_KEY not found in .env file.")

def convert_xml_to_db(xml_path, db_path, encryption_key):
    # Parse XML first (outside of connection for better error isolation)
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    translation_name = root.attrib.get('translation', 'Unknown')
    status = root.attrib.get('status', 'Unknown')
    
    # Delete existing DB if it exists
    if db_path.exists():
        db_path.unlink()
    
    # Connect and Apply encryption
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA key = '{encryption_key}'")
    
    # Create tables
    cursor.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)')
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
    
    # Insert metadata
    cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)', ('translation', translation_name))
    cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)', ('status', status))
    
    # Process verses
    verses_to_insert = []
    testaments = root.findall('testament')
    if testaments:
        for testament in testaments:
            testament_name = testament.attrib.get('name')
            for book in testament.findall('book'):
                book_num = int(book.attrib.get('number'))
                for chapter in book.findall('chapter'):
                    chapter_num = int(chapter.attrib.get('number'))
                    for verse in chapter.findall('verse'):
                        verses_to_insert.append((
                            testament_name, book_num, chapter_num, 
                            int(verse.attrib.get('number')), verse.text or ""
                        ))
    else:
        for book in root.findall('book'):
            book_num = int(book.attrib.get('number'))
            testament_name = "Old" if book_num <= 39 else "New"
            for chapter in book.findall('chapter'):
                chapter_num = int(chapter.attrib.get('number'))
                for verse in chapter.findall('verse'):
                    verses_to_insert.append((
                        testament_name, book_num, chapter_num, 
                        int(verse.attrib.get('number')), verse.text or ""
                    ))
    
    cursor.executemany('''
        INSERT INTO verses (testament, book_number, chapter_number, verse_number, text)
        VALUES (?, ?, ?, ?, ?)
    ''', verses_to_insert)
    
    conn.commit()
    conn.close()
    return len(verses_to_insert)

if __name__ == "__main__":
    start_time = time.perf_counter()
    try:
        encryption_key = get_encryption_key()
    except Exception as e:
        print(f"Error loading encryption key: {e}")
        exit(1)

    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    xml_dir = project_dir / "Holy-Bible-XML-Format"
    db_dir = project_dir / "database"
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
