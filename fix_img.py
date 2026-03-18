with open('d:/Projects/Assitance/backend/app/tools/image_gen.py', 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace('http://127.0.0.1:8321/api/images/', '/api/images/')
code = code.replace('http://127.0.0.1:8322/api/images/', '/api/images/')
with open('d:/Projects/Assitance/backend/app/tools/image_gen.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Fixed image URL format!')
