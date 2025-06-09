import sqlite3
from pathlib import Path
from tabulate import tabulate
from datetime import datetime

def clear_database():
    """Delete all records from the database"""
    db_path = Path('data/measurements.db')
    if not db_path.exists():
        print("Database file not found.")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Delete all records
        cursor.execute('DELETE FROM detections')
        conn.commit()
        print("All records have been deleted from the database.")

    except Exception as e:
        print(f"Error clearing database: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

def view_database():
    """View the contents of the measurements database"""
    db_path = Path('data/measurements.db')
    if not db_path.exists():
        print("Database file not found.")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get all records
        cursor.execute('''
            SELECT id, waste_type, confidence_level, contamination, classification, timestamp
            FROM detections
            ORDER BY timestamp DESC
        ''')
        
        rows = cursor.fetchall()
        
        if not rows:
            print("No records found in the database.")
            return

        # Format the data for display
        headers = ['ID', 'Type', 'Confidence', 'Contamination', 'Classification', 'Timestamp']
        formatted_rows = []
        
        for row in rows:
            # Format timestamp
            timestamp = datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S')
            formatted_timestamp = timestamp.strftime('%m-%d %H:%M:%S')
            
            # Format contamination as percentage
            contamination = f"{float(row[3]):.2f}%"
            
            formatted_rows.append([
                row[0],  # ID
                row[1],  # Type
                row[2],  # Confidence
                contamination,  # Contamination
                row[4],  # Classification
                formatted_timestamp  # Timestamp
            ])

        # Print the table
        print("\nDatabase Contents:")
        print(tabulate(formatted_rows, headers=headers, tablefmt='grid'))
        print(f"\nTotal records: {len(rows)}")

    except Exception as e:
        print(f"Error viewing database: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    view_database()   # Show database contents 
    #clear_database()  # Delete all records
    