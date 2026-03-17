import sqlite3
import os
from datetime import datetime

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'assistance.db'))
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

now = datetime.now().isoformat()

# 1. Update ALLOWED Gemini models in model_configs
print("Cleaning up model_configs...")
cursor.execute("DELETE FROM model_configs WHERE provider = 'gemini'")

# Full set of allowed Gemini models (2.5+)
# context_window: 1048576
allowed_gemini = [
    # id, provider, name, context_window, is_vision, is_active
    ('gemini-2.5-flash', 'gemini', 'Gemini 2.5 Flash', 1048576, 1, 1),
    ('gemini-2.5-flash-lite', 'gemini', 'Gemini 2.5 Flash Lite', 1048576, 1, 1),
    ('gemini-2.5-pro', 'gemini', 'Gemini 2.5 Pro', 1048576, 1, 1),
    ('gemini-3-flash-preview', 'gemini', 'Gemini 3 Flash Preview', 1048576, 1, 1),
    ('gemini-3-pro-preview', 'gemini', 'Gemini 3 Pro Preview', 1048576, 1, 1),
    ('gemini-3.1-flash-preview', 'gemini', 'Gemini 3.1 Flash Preview', 1048576, 1, 1),
    ('gemini-3.1-pro-preview', 'gemini', 'Gemini 3.1 Pro Preview', 1048576, 1, 1),
    ('gemini-3.1-flash-lite', 'gemini', 'Gemini 3.1 Flash Lite', 1048576, 1, 1),
]

for model_id, provider, name, cw, vision, active in allowed_gemini:
    cursor.execute(
        """INSERT INTO model_configs 
           (id, provider, name, context_window, is_vision, is_active, created_at, updated_at) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (model_id, provider, name, cw, vision, active, now, now)
    )

# 2. Update Agents
print("Reviewing agents...")
cursor.execute("SELECT id, name, model FROM agents")
agents = cursor.fetchall()
allowed_ids = [a[0] for a in allowed_gemini]

for agent_id, agent_name, agent_model in agents:
    if agent_model.startswith('gemini/'):
        m = agent_model.replace('gemini/', '')
        # If model is not in our allowed list, update it to the requested minimum 2.5 Flash Lite
        if m not in allowed_ids:
            print(f"Updating agent '{agent_name}' ({agent_id}) from {agent_model} to gemini/gemini-2.5-flash-lite")
            cursor.execute("UPDATE agents SET model = 'gemini/gemini-2.5-flash-lite' WHERE id = ?", (agent_id,))
        else:
            print(f"Agent '{agent_name}' is already on an allowed model: {agent_model}")

conn.commit()
conn.close()

print("Database update complete.")
