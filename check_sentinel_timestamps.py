
import sqlite3
import os

db_path = "data/assistance.db"

def check_timestamps():
    try:
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}")
            return
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT created_at, COUNT(*) FROM messages WHERE agent_name LIKE '%Sentinel%' AND (content IS NULL OR content = '' OR content = ' ') GROUP BY created_at ORDER BY created_at LIMIT 50")
        rows = cur.fetchall()
        
        print(f"--- Sentinel Empty Message Timestamps ---")
        for row in rows:
            print(f"Time: {row[0]} | Count: {row[1]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_timestamps()
