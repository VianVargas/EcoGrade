import sqlite3
from pathlib import Path

def migrate_database():
    """Migrate the database to rename opacity column to confidence_level and clear old data"""
    db_path = Path('data/measurements.db')
    if not db_path.exists():
        print("Database file not found. No migration needed.")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Drop the old table
        cursor.execute('DROP TABLE IF EXISTS detections')
        
        # Create new table with updated schema
        cursor.execute('''
            CREATE TABLE detections (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                waste_type TEXT,
                confidence_level TEXT,
                contamination REAL,
                classification TEXT
            )
        ''')
        
        conn.commit()
        print("Database migration completed successfully - old data cleared and new schema created")

    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database() 