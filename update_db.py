import sqlite3
from pathlib import Path

def update_database():
    db_path = Path('data/measurements.db')
    if not db_path.exists():
        print("Database file not found")
        return

    try:
        # Connect to the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # First, check if there are any records with "High Value Recyclable"
        cursor.execute("SELECT COUNT(*) FROM detections WHERE classification = 'High Value Recyclable'")
        count = cursor.fetchone()[0]
        print(f"Found {count} records with 'High Value Recyclable' classification")

        if count > 0:
            # Update the records
            cursor.execute("""
                UPDATE detections 
                SET classification = 'High Value' 
                WHERE classification = 'High Value Recyclable'
            """)
            conn.commit()
            print(f"Updated {count} records from 'High Value Recyclable' to 'High Value'")
        else:
            print("No records found with 'High Value Recyclable' classification")

        # Verify the update
        cursor.execute("SELECT COUNT(*) FROM detections WHERE classification = 'High Value'")
        new_count = cursor.fetchone()[0]
        print(f"Total records with 'High Value' classification: {new_count}")

        conn.close()
        print("Database update completed successfully")

    except Exception as e:
        print(f"Error updating database: {str(e)}")

if __name__ == "__main__":
    update_database() 