import os

files = [
    'skills.html', 'projects.html', 'education.html', 'publications.html', 
    'workshops.html', 'gallery.html', 'summary.html', 'contact.html', 'bio.html'
]

old_tag = '<script src="https://d3js.org/d3.v7.min.js"></script>'
new_tags = '<script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>\n    <script src="https://unpkg.com/3d-force-graph@1.73.0/dist/3d-force-graph.min.js"></script>'

for f in files:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        if old_tag in content:
            print(f"Updating {f}")
            new_content = content.replace(old_tag, new_tags)
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
        else:
            print(f"Target tag not found in {f}")
    else:
        print(f"File {f} not found")
