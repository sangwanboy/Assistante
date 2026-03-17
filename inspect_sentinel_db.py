
import sqlite3
import os

# Use absolute path for reliability on Windows
db_path = r"d:\Projects\Assitance\data\assistance.db"

def inspect_sentinel():
    try:
        if not os.path.exists(db_path):
            # Try recursive search if first guess fails
            print(f"Database not found at {db_path}. Searching...")
            return
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get Sentinel info
        cur.execute("SELECT id, name, system_prompt, description, is_system FROM agents WHERE name LIKE '%Sentinel%'")
        rows = cur.fetchall()
        
        print(f"--- Sentinel Agent Investigation ---")
        if not rows:
            print("Sentinel not found.")
        for row in rows:
            print(f"ID: {row[0]}")
            print(f"Name: {row[1]}")
            print(f"System: {row[4]}")
            print(f"Prompt: {row[2][:200]}...")
            print(f"Description: {row[3]}")
            print("-" * 20)
            
            # Check messages for this specific agent
            cur.execute("SELECT COUNT(*), COUNT(CASE WHEN content='' OR content IS NULL THEN 1 END) FROM messages WHERE agent_name=?", (row[1],))
            counts = cur.fetchone()
            print(f"Messages: {counts[0]} total, {counts[1]} empty")
            
            # Get latest 5 non-empty messages
            cur.execute("SELECT content, created_at FROM messages WHERE agent_name=? AND content != '' AND content IS NOT NULL ORDER BY created_at DESC LIMIT 5", (row[1],))
            msgs = cur.fetchall()
            print("Latest non-empty messages:")
            for m in msgs:
                print(f"[{m[1]}] {m[0][:100]}...")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_sentinel()
