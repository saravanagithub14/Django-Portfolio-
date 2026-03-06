import glob

files = glob.glob('*.html')
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'href="https://medium.com"' in content:
        content = content.replace('href="https://medium.com"', 'href="https://medium.com/@mynamesaravanaperumal"')
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)

print('Updated Medium link in all HTML files.')
