import sqlite3
import random
import string
import os

def generate_unique_id(existing):
    while True:
        new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if new_id not in existing:
            return new_id

def main():
    db_path = os.path.join('data', 'measurements.db')
    if not os.path.exists(db_path):
        print('Database not found:', db_path)
        return
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT id FROM detections')
    ids = [row[0] for row in c.fetchall()]
    existing = set(ids)
    new_ids = {}
    for old in ids:
        new = generate_unique_id(existing)
        new_ids[old] = new
        existing.add(new)
    for old, new in new_ids.items():
        c.execute('UPDATE detections SET id=? WHERE id=?', (new, old))
    conn.commit()
    conn.close()
    print(f'Updated {len(new_ids)} IDs to unique 4-character alphanumeric values.')

if __name__ == '__main__':
    main() 