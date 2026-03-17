import asyncio
import sqlite3
import os

db_path = r"d:\Projects\Assitance\backend\data\assitance.db"

def check():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Message Tables Schema ---")
    for table in ["agent_messages", "messages"]:
        try:
            print(f"\nTable: {table}")
            cursor.execute(f"PRAGMA table_info({table});")
            for row in cursor.fetchall():
                print(row)
        except Exception as e:
            print(f"Error checking {table}: {e}")
    
    conn.close()

if __name__ == "__main__":
    check()
