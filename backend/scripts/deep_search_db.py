import sqlite3
import os

db_path = r'd:\Projects\Assitance\backend\data\assistance.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ['agents', 'model_configs', 'conversations', 'messages']
search_term = 'gemini-2.0-flash'

found = False
for table in tables:
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        
        for col in columns:
            query = f"SELECT * FROM {table} WHERE \"{col}\" LIKE ?"
            cursor.execute(query, (f'%{search_term}%',))
            rows = cursor.fetchall()
            if rows:
                print(f"Found in {table}.{col}:")
                for row in rows:
                    print(row)
                found = True
    except Exception as e:
        print(f"Error searching {table}: {e}")

if not found:
    print(f"No references to '{search_term}' found in any searched tables.")

conn.close()
