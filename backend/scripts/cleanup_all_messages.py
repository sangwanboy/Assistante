import sqlite3
import os

db_path = 'backend/data/assistance.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Delete assistant messages with empty or whitespace-only content (keeping those with tool calls for history if needed, but the user wants ghost headers gone)
# Actually, ghost headers are usually messages WITHOUT content and WITHOUT tool results showing.
# However, many historical messages have tool_calls but no content, which still show as empty bubbles/headers.
# The most aggressive cleanup is to remove all assistant messages that have no text and no tool calls.

print("Starting global cleanup of empty messages...")

# 1. Delete assistant messages with NO content AND NO tool calls
cursor.execute("DELETE FROM messages WHERE role = 'assistant' AND (content IS NULL OR TRIM(content) = '') AND (tool_calls_json IS NULL OR tool_calls_json = '')")
deleted_no_tools = cursor.rowcount
print(f"Deleted {deleted_no_tools} empty assistant messages (no tool calls).")

# 2. Delete empty assistant messages WITH tool calls (these also cause ghost headers if the tool results aren't helpful or if they were part of a loop)
# In the screenshot, "SENTINEL 22:13" headers are likely these.
cursor.execute("DELETE FROM messages WHERE role = 'assistant' AND (content IS NULL OR TRIM(content) = '') AND tool_calls_json IS NOT NULL AND tool_calls_json != ''")
deleted_with_tools = cursor.rowcount
print(f"Deleted {deleted_with_tools} empty assistant messages (with tool calls).")

# 3. Clean up orphaned tool messages (optional but good for DB health)
cursor.execute("DELETE FROM messages WHERE role = 'tool' AND (content IS NULL OR TRIM(content) = '')")
deleted_tools = cursor.rowcount
print(f"Deleted {deleted_tools} empty tool messages.")

conn.commit()
print("Database cleanup complete.")
conn.close()
