import glob
import re

button_html = """    <!-- Graph View at the bottom -->
    <div style="text-align: center; margin-top: 80px; margin-bottom: 20px;">
        <div style="font-size: 1.5rem; color: #e8e0ff; margin-bottom: 12px;">Explore the Graph</div>
        <button onclick="window.scrollTo({top: 0, behavior: 'smooth'})" style="background: rgba(100, 60, 200, 0.2); border: 1px solid rgba(140, 100, 255, 0.3); color: rgba(200, 192, 232, 0.8); padding: 8px 24px; border-radius: 30px; cursor: pointer; font-family: 'Inter', sans-serif; font-size: 0.75rem; transition: all 0.3s; letter-spacing: 1.5px; text-transform: uppercase; outline: none; box-shadow: 0 4px 15px rgba(0,0,0,0.2);" onmouseover="this.style.background='rgba(140, 100, 255, 0.4)'; this.style.color='#fff'; this.style.transform='translateY(-2px)';" onmouseout="this.style.background='rgba(100, 60, 200, 0.2)'; this.style.color='rgba(200, 192, 232, 0.8)'; this.style.transform='translateY(0)';">↑ Back to Top</button>
    </div>"""

# Ensure we handle multiple variants of the old block precisely
old_pattern = re.compile(r'<!--\s*Graph View at the bottom\s*-->\s*<div style="text-align: center; margin-top: 80px; font-size: 1.5rem; color: #e8e0ff;( font-family:\s*\'Trench Thin\',\s*\'Inter\',\s*sans-serif;)?">Explore the Graph</div>.*?$', re.MULTILINE)

files = glob.glob('*.html')
for file in files:
    if file == 'index.html': continue
    
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the block we need to replace
    # We can just do a str.replace
    
    variant_1 = '<!-- Graph View at the bottom -->\n    <div style="text-align: center; margin-top: 80px; font-size: 1.5rem; color: #e8e0ff;">Explore the Graph</div>'
    variant_2 = '<!-- Graph View at the bottom -->\n    <div style="text-align: center; margin-top: 80px; font-size: 1.5rem; color: #e8e0ff; font-family: \'Trench Thin\', \'Inter\', sans-serif;">Explore the Graph</div>'
    
    if variant_1 in content:
        content = content.replace(variant_1, button_html)
    elif variant_2 in content:
        content = content.replace(variant_2, button_html)

    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)

print('Added Back to Top button to inner pages')
