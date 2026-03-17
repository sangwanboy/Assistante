import sqlite3
import json

db_path = 'd:/Projects/Assitance/backend/data/assitance.db'

def update_agents():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Update Janny (System Orchestrator)
    janny_tools = [
        "AgentManagerTool", 
        "AgentDelegationTool", 
        "ModelManagerTool", 
        "AgentMessengerTool", 
        "SessionStatusTool", 
        "SystemConfigTool", 
        "image_gen", 
        "video_gen"
    ]
    cursor.execute(
        "UPDATE agents SET enabled_tools = ? WHERE name LIKE 'Janny%'",
        (json.dumps(janny_tools),)
    )
    print(f"Updated Janny's tools. Rows affected: {cursor.rowcount}")
    
    # 2. Update Content Creator
    creator_tools = ["image_gen", "video_gen"]
    cursor.execute(
        "UPDATE agents SET enabled_tools = ? WHERE name = 'Content Creator'",
        (json.dumps(creator_tools),)
    )
    print(f"Updated Content Creator's tools. Rows affected: {cursor.rowcount}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_agents()
