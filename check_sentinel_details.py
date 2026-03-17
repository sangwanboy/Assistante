
import sqlite3
import os

db_path = r"d:\Projects\Assitance\backend\data\assistance.db"

def check_messages():
    try:
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}")
            return
            
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT id, role, content, agent_name, tool_call_id FROM messages WHERE agent_name LIKE '%Sentinel%' AND (content IS NULL OR content = '' OR content = ' ') LIMIT 20")
        rows = cur.fetchall()
        
        print(f"--- Sentinel Empty Message Samples ---")
        for row in rows:
            print(f"ID: {row[0]} | Role: {row[1]} | Agent: {row[3]} | ToolID: {row[4]}")
            
        # Also check if they are related to a specific conversation
        cur.execute("SELECT conversation_id, COUNT(*) FROM messages WHERE agent_name LIKE '%Sentinel%' AND (content IS NULL OR content = '' OR content = ' ') GROUP BY conversation_id")
        convs = cur.fetchall()
        print("\nConversations affected:")
        for c in convs:
            print(f"ConvID: {c[0]} | Count: {c[1]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_messages()
