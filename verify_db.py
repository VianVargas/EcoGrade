import sqlite3
from pathlib import Path

def verify_database():
    db_path = Path('data/measurements.db')
    if not db_path.exists():
        print("Database file not found")
        return

    try:
        # Connect to the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get count of each classification
        cursor.execute("""
            SELECT classification, COUNT(*) as count 
            FROM detections 
            GROUP BY classification 
            ORDER BY count DESC
        """)
        
        print("\nCurrent classification counts in database:")
        print("-" * 40)
        for classification, count in cursor.fetchall():
            print(f"{classification}: {count} records")
        print("-" * 40)

        conn.close()

    except Exception as e:
        print(f"Error verifying database: {str(e)}")

if __name__ == "__main__":
    verify_database() 