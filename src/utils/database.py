import sqlite3
import pandas as pd
import os
from datetime import datetime
import random
import string

def save_detection_to_excel(detection_data, excel_path='detections.xlsx'):
    """
    Save a detection result to an Excel file. If the file doesn't exist, create it with headers.
    detection_data: dict with keys: id, timestamp, waste_type, result, and other criteria.
    """
    columns = [
        'id', 'timestamp', 'waste_type', 'result', 'contamination_score', 'classification'
    ]
    # Add any extra keys from detection_data
    for k in detection_data.keys():
        if k not in columns:
            columns.append(k)
    row = {col: detection_data.get(col, '') for col in columns}
    if os.path.exists(excel_path):
        df = pd.read_excel(excel_path)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row], columns=columns)
    df.to_excel(excel_path, index=False)

def store_measurement(result_data):
    """Store detection result in SQLite database"""
    try:
        conn = sqlite3.connect('data/measurements.db')
        c = conn.cursor()
        
        # Check if detection with this ID already exists
        c.execute('SELECT id FROM detections WHERE id = ?', (str(result_data['id']),))
        
        if not c.fetchone():
            # Only insert if it's a new detection
            try:
                # Get confidence level from the detection result
                confidence = result_data.get('confidence_level', '0%')
                if isinstance(confidence, float):
                    confidence = f"{confidence:.1f}%"
                
                c.execute('''INSERT INTO detections (id, timestamp, waste_type, confidence_level, contamination, classification)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (str(result_data['id']), result_data['timestamp'], result_data['waste_type'],
                           confidence, float(result_data['contamination_score']), result_data['classification']))
                conn.commit()
            except sqlite3.IntegrityError:
                # If there's still a conflict, skip this insertion
                pass
    except Exception as e:
        print(f"Error storing measurement: {str(e)}")
    finally:
        conn.close()

def generate_unique_id(object_trackers=None, finalized_ids=None):
    """Generate a unique 4-character alphanumeric ID"""
    if object_trackers is None:
        object_trackers = {}
    if finalized_ids is None:
        finalized_ids = set()
        
    while True:
        new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if new_id not in object_trackers and new_id not in finalized_ids:
            return new_id 