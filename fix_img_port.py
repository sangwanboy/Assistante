with open('d:/Projects/Assitance/backend/app/tools/image_gen.py', 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace('8322', '8321')
with open('d:/Projects/Assitance/backend/app/tools/image_gen.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Fixed backend image gen port!')
