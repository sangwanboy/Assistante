with open('app/tools/workspace_tools.py', 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace('task_id = kwargs.get("_task_id")', 'task_id = kwargs.get("_task_id") or kwargs.get("conversation_id")')
with open('app/tools/workspace_tools.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Done!')
