import sqlite3
import os

db_path = r'backend/data/assistance.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Current Agent Models:")
cursor.execute("SELECT id, name, model FROM agents")
agents = cursor.fetchall()
for id, name, model in agents:
    print(f"Agent: {name} (ID: {id}), Model: {model}")

print("\nScanning for models lower than 2.5 or decommissioned models...")
# We want only 2.5 or above. Anything else should be updated.
to_update = []
for id, name, model in agents:
    # Check for gemini-2.0, gemini-1.5, etc.
    if 'gemini-1.' in model or 'gemini-2.0' in model:
         to_update.append((id, name, model))

if to_update:
    print(f"Found {len(to_update)} agents to update.")
    for id, name, model in to_update:
        new_model = "gemini/gemini-2.5-flash"
        print(f"Updating {name}: {model} -> {new_model}")
        cursor.execute("UPDATE agents SET model = ? WHERE id = ?", (new_model, id))
    conn.commit()
    print("Database updated.")
else:
    print("No outdated models found in agents table.")

conn.close()
