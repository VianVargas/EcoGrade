import sqlite3
from pathlib import Path

def init_database():
    """Initialize the database with the correct schema"""
    db_path = Path('data/measurements.db')
    db_path.parent.mkdir(exist_ok=True)
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create the detections table with the correct schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                waste_type TEXT,
                confidence_level TEXT,
                contamination REAL,
                classification TEXT
            )
        ''')
        
        conn.commit()
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_database() 