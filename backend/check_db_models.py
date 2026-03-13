
import sqlite3
import os

db_path = "d:/Projects/Assitance/backend/data/assitance.db"

def check():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Check Agent
        cursor.execute("SELECT * FROM agents WHERE name = 'Janny Connan'")
        agent = cursor.fetchone()
        if agent:
            print(f"Agent: {agent['name']}")
            print(f"Provider: {agent['provider']}")
            print(f"Model ID: {agent['model']}")
        else:
            print("Agent 'Janny Connan' not found")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check()
