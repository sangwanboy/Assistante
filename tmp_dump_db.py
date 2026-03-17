import sqlite3
import os

db_path = r"d:\Projects\Assitance\backend\data\assistance.db"

def dump():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open("db_dump.txt", "w", encoding="utf-8") as f:
        f.write("=== AGENTS ===\n")
        cursor.execute("SELECT id, name, is_system, is_active FROM agents")
        for row in cursor.fetchall():
            f.write(f"{row}\n")
            
        f.write("\n=== SCHEDULES ===\n")
        cursor.execute("SELECT id, name, agent_id, interval_minutes, is_active FROM agent_schedules")
        for row in cursor.fetchall():
            f.write(f"{row}\n")
            
        f.write("\n=== MESSAGE COUNTS PER CONVERSATION ===\n")
        cursor.execute("SELECT conversation_id, COUNT(*) FROM agent_messages GROUP BY conversation_id")
        for row in cursor.fetchall():
            f.write(f"{row}\n")

    conn.close()

if __name__ == "__main__":
    dump()
