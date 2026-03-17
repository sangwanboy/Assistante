import sqlite3
import json

db_path = "d:/Projects/Assitance/backend/data/assitance.db"
agent_id = "d1781a5b-6ab6-426e-8dec-0a2198a9d93a"

def update_janny():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # New tool list: existing + SystemConfigTool
    tools = [
        "AgentManagerTool", 
        "AgentDelegationTool", 
        "ModelManagerTool", 
        "AgentMessengerTool", 
        "SessionStatusTool", 
        "SystemConfigTool"
    ]
    
    instr = (
        "You can now use the SystemConfigTool to save or update system-wide API keys "
        "(e.g. 'brave_search') provided by the user in chat. When a user gives you an API key, "
        "use this tool to persist it so that search/vision tools can function correctly."
    )
    
    try:
        cursor.execute(
            "UPDATE agents SET enabled_tools = ?, memory_instructions = ? WHERE id = ?",
            (json.dumps(tools), instr, agent_id)
        )
        conn.commit()
        print("Successfully updated Janny's tools and instructions.")
    except Exception as e:
        print(f"Error updating Janny: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_janny()
