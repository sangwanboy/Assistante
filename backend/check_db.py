import sqlite3
import os

db_path = 'assistance.db'
if os.path.exists(db_path):
    print(f"--- Checking {db_path} ---")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    if 'external_integrations' in tables:
        cursor.execute("SELECT * FROM external_integrations")
        print(cursor.fetchall())
    conn.close()
else:
    print(f"File not found: {db_path}")
