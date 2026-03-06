import glob

with open('index.html', 'r', encoding='utf-8') as f:
    idx = f.read()

idx = idx.replace('href="bio.html"', 'href="#bio-section"')
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(idx)

for file in glob.glob('*.html'):
    if file == 'index.html': continue
    with open(file, 'r', encoding='utf-8') as f:
        c = f.read()
    c = c.replace('href="bio.html"', 'href="index.html#bio-section"')
    with open(file, 'w', encoding='utf-8') as f:
        f.write(c)

print('Fixed h-refs')
