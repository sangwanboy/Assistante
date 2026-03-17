
import sqlite3
import os

db_path = r"d:\Projects\Assitance\backend\data\assistance.db"

def cleanup():
    try:
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}")
            return
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Count before
        cur.execute("SELECT COUNT(*) FROM messages WHERE (content IS NULL OR content = '' OR content = ' ')")
        before = cur.fetchone()[0]
        
        # Delete empty messages from Sentinel specifically (or all agents if desired, but Sentinel is the spammer)
        cur.execute("DELETE FROM messages WHERE agent_name LIKE '%Sentinel%' AND (content IS NULL OR content = '' OR content = ' ')")
        deleted = cur.rowcount
        
        conn.commit()
        print(f"Cleanup results for Sentinel:")
        print(f"- Total empty messages found in DB: {before}")
        print(f"- Empty Sentinel messages deleted: {deleted}")
        
        # Check remaining Sentinel messages
        cur.execute("SELECT COUNT(*) FROM messages WHERE agent_name LIKE '%Sentinel%'")
        remaining = cur.fetchone()[0]
        print(f"- Remaining Sentinel messages: {remaining}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cleanup()
