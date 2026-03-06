import glob

files = glob.glob('*.html')
for file in files:
    if file == 'index.html': continue
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'style.css' not in content:
        content = content.replace('</head>', '    <link rel="stylesheet" href="style.css">\n</head>')
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)

print('Added style.css to inner pages')
