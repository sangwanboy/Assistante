import sqlite3
import os

db_path = "data/assistance.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]
    for table in tables:
        print(f"Table: {table}")
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        for col in cols:
            print(f"  {col[1]}")
    conn.close()
else:
    print(f"Database not found at {db_path}")
