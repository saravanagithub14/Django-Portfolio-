import os
import re

# 1. Merge Bio into Index

with open('bio.html', 'r', encoding='utf-8') as f:
    bio_content = f.read()

with open('index.html', 'r', encoding='utf-8') as f:
    index_content = f.read()

# Extract .content from bio.html
# Find the start of <div class="content"> and its closing tag.
# Also extract the <style> block from bio.html to add to style.css or index.html
bio_style_match = re.search(r'<style>(.*?)</style>', bio_content, re.DOTALL)
if bio_style_match:
    bio_style = bio_style_match.group(1)
    # Append bio specific styles to style.css
    with open('style.css', 'a', encoding='utf-8') as f:
        f.write("\n/* --- Bio Styles --- */\n" + bio_style)

# Extract content
# Since we know bio.html, we can use a regex to get everything between <div class="content"> and the end of the content div, typically before the script tags.
content_match = re.search(r'(<div class="content">.*?)<script>', bio_content, re.DOTALL)
if content_match:
    bio_inner = content_match.group(1)
    # The bio_inner contains the `.content` div.
    
    # Let's clean up back buttons or nav links from it if needed, or leave it.
    # We want index.html to have this below #instructions.
    index_content = index_content.replace('<!-- Instructions -->', '<!-- Instructions -->\n    ' + bio_inner)

# Ensure data.js points to bio section for 'Bio' node instead of bio.html
with open('data.js', 'r', encoding='utf-8') as f:
    data_content = f.read()
data_content = data_content.replace('"navigateTo": "bio.html"', '"navigateTo": "#bio-section"')
with open('data.js', 'w', encoding='utf-8') as f:
    f.write(data_content)

# Add an id to the bio content div so we can navigate to it
index_content = index_content.replace('<div class="content">', '<div class="content" id="bio-section">')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(index_content)


# 2. Add Graph View to all inner pages
graph_append = """
    <!-- Graph View at the bottom -->
    <div style="text-align: center; margin-top: 80px; font-size: 1.5rem; color: #e8e0ff;">Explore the Graph</div>
    <div id="graph-container" style="height: 70vh; width: 100vw; position: relative; left: 50%; right: 50%; margin-left: -50vw; margin-right: -50vw;"></div>
    
    <!-- Info Panel -->
    <div id="info-panel">
        <span class="close-btn" onclick="document.getElementById('info-panel').style.display='none'">&times;</span>
        <h2 id="panel-title">Title</h2>
        <div id="panel-content">Content goes here...</div>
    </div>

    <!-- Instructions -->
    <div id="instructions" style="position: relative; text-align: center; margin-bottom: 20px; color: rgba(255,255,255,0.4);">
        Drag to move &bull; Scroll to zoom &bull; Click nodes to explore
    </div>

    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="data.js"></script>
    <script src="script.js"></script>
"""

files = ['skills.html', 'experience.html', 'education.html', 'projects.html', 'publications.html', 'workshops.html', 'contact.html', 'summary.html']

for file in files:
    if not os.path.exists(file): continue
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # insert before <script src="snowfall.js"></script> or </body>
    if '<script src="snowfall.js"></script>' in content:
        content = content.replace('<script src="snowfall.js"></script>', graph_append + '\n    <script src="snowfall.js"></script>')
    else:
        content = content.replace('</body>', graph_append + '\n</body>')
        
    # update nav-link to use index.html#bio-section instead of bio.html
    content = content.replace('href="bio.html"', 'href="index.html#bio-section"')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

print('Updated index and inner pages successfully.')
