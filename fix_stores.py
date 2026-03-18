import os
files = ['d:/Projects/Assitance/frontend/src/stores/agentControlStore.ts', 'd:/Projects/Assitance/frontend/src/stores/workflowStore.ts']
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('8322', '8321')
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
print('Fixed frontend stores!')
