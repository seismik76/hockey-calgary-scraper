from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os
import shutil
import sqlite3

DB_FILE = "hockey_calgary.db"
SEED_FILE = "data/seed/hockey_calgary.db"
DB_URL = f"sqlite:///{DB_FILE}"

def is_db_populated(db_path):
    if not os.path.exists(db_path):
        return False
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Check if seasons table exists and has data
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='seasons';")
        if not cursor.fetchone():
            conn.close()
            return False
        
        cursor.execute("SELECT count(*) FROM seasons;")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False

# Auto-restore from seed if DB is missing OR empty
if not is_db_populated(DB_FILE):
    if os.path.exists(SEED_FILE):
        print(f"Database missing or empty. Initializing from seed: {SEED_FILE}")
        try:
            # Ensure we don't have open connections if we are overwriting
            if os.path.exists(DB_FILE):
                try:
                    os.remove(DB_FILE) # Remove empty/corrupt file
                except PermissionError:
                    print("Warning: Could not remove existing DB file. It might be in use.")
            
            shutil.copy2(SEED_FILE, DB_FILE)
            print("Database restored successfully.")
        except Exception as e:
            print(f"Error restoring database from seed: {e}")
    else:
        print("Database not found and no seed file available. A new empty database will be created.")

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
