import sqlcipher3 as sqlite3
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

def read_encrypted_db(db_path, key):
    print(f"--- Reading Database: {db_path.name} ---")
    
    try:
        # Connect to the encrypted database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Authenticate with the key
        cursor.execute(f"PRAGMA key = '{key}'")
        
        # Test query: Fetch metadata
        cursor.execute("SELECT key, value FROM metadata")
        metadata = cursor.fetchall()
        print("\nMetadata:")
        for k, v in metadata:
            print(f"  {k}: {v}")
            
        # Select first 5 verses
        cursor.execute("""
            SELECT testament, book_number, chapter_number, verse_number, text 
            FROM verses 
            LIMIT 5
        """)
        verses = cursor.fetchall()
        
        print("\nSample Verses:")
        for v in verses:
            print(f"  [{v[0]}] Book {v[1]} Ch {v[2]}:{v[3]} -> {v[4][:80]}...")
            
        conn.close()
        print("\n--- Read Successful ---")
        
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == "__main__":
    try:
        encryption_key = get_encryption_key()
        
        # Find the first database in the directory
        db_dir = Path("database")
        db_files = list(db_dir.glob("*.db"))
        
        if not db_files:
            print("No database files found in 'database' folder.")
        else:
            # pick the first one for demonstration
            sample_db = db_files[0]
            read_encrypted_db(sample_db, encryption_key)
            
    except Exception as e:
        print(f"Error: {e}")
