from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os
import shutil

DB_FILE = "hockey_calgary.db"
SEED_FILE = "data/seed/hockey_calgary.db"
DB_URL = f"sqlite:///{DB_FILE}"

# Auto-restore from seed if DB is missing
if not os.path.exists(DB_FILE):
    if os.path.exists(SEED_FILE):
        print(f"Database not found. Initializing from seed: {SEED_FILE}")
        try:
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
