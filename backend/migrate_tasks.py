import sqlite3
import os

db_path = "data/assitance.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add missing columns to 'tasks' table
    columns_to_add = [
        ("last_heartbeat_at", "DATETIME"),
        ("step_started_at", "DATETIME"),
        ("cancel_requested", "BOOLEAN DEFAULT 0"),
        ("lock_key", "VARCHAR"),
        ("step_idempotent", "BOOLEAN DEFAULT 1")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            print(f"Adding column '{col_name}' to 'tasks'...")
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
            print(f"Successfully added '{col_name}'.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column '{col_name}' already exists.")
            else:
                print(f"Error adding '{col_name}': {e}")
    
    conn.commit()
    conn.close()
    print("Migration complete.")
else:
    print(f"Database not found at {db_path}")
