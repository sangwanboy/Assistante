import sqlite3
import os
import json

db_path = "data/assistance.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check active tasks
    cursor.execute("SELECT id, assigned_agent_id, status, lifecycle_stage, goal, updated_at FROM tasks WHERE status IN ('QUEUED', 'RUNNING', 'WAITING_TOOL', 'WAITING_CHILD')")
    active_tasks = cursor.fetchall()
    print(f"Active Tasks ({len(active_tasks)}):")
    for task in active_tasks:
        print(f"  ID: {task[0]}, Agent: {task[1]}, Status: {task[2]}, Stage: {task[3]}, Goal: {task[4][:50]}..., Updated: {task[5]}")
        
    # Check agent statuses (if possible via DB, though AgentStatusManager might be in Redis/In-memory)
    # Most status info is often just in the 'agents' table too
    cursor.execute("SELECT id, name, status, last_heartbeat FROM agents")
    agents = cursor.fetchall()
    print("\nAgent Statuses (DB):")
    for agent in agents:
        print(f"  {agent[1]} ({agent[0]}): Status={agent[2]}, Last Heartbeat={agent[3]}")
        
    conn.close()
else:
    print(f"Database not found at {db_path}")
