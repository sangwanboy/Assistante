with open('app/tools/image_gen.py', 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace('Google Imagen 3', 'Google Imagen 4')
with open('app/tools/image_gen.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Done!')
