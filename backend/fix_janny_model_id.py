
import sqlite3
import os

db_path = "d:/Projects/Assitance/backend/data/assitance.db"

def update_janny():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        new_model = "gemini/gemini-3.1-flash-lite-preview"
        print(f"Updating Janny Connan model to: {new_model}")
        cursor.execute("UPDATE agents SET model = ? WHERE name = 'Janny Connan'", (new_model,))
        conn.commit()
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_janny()
