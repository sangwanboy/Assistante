
import sqlite3
import os

db_path = "data/assistance.db"

def find_sentinel():
    try:
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}")
            return
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT id, name, is_system, model, description FROM agents WHERE name LIKE '%Sentinel%'")
        rows = cur.fetchall()
        
        print(f"--- Sentinel Agent Info ---")
        if not rows:
            print("No agent found with name 'Sentinel'")
        for row in rows:
            print(f"ID: {row[0]} | Name: {row[1]} | System: {row[2]} | Model: {row[3]}")
            print(f"Description: {row[4]}")
            print("-" * 20)
            
        # Check for message counts
        cur.execute("SELECT COUNT(*) FROM messages WHERE agent_name LIKE '%Sentinel%'")
        msg_count = cur.fetchone()[0]
        print(f"Total messages for Sentinel: {msg_count}")
        
        # Check empty messages
        cur.execute("SELECT COUNT(*) FROM messages WHERE agent_name LIKE '%Sentinel%' AND (content IS NULL OR content = '' OR content = ' ')")
        empty_count = cur.fetchone()[0]
        print(f"Empty messages for Sentinel: {empty_count}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_sentinel()
