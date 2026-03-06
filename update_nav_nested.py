import glob
import re

css_to_add = """
/* Dropdown Navigation */
.dropdown {
    position: relative;
    display: inline-block;
}

.dropbtn {
    background: none;
    border: none;
    font-family: inherit;
    cursor: pointer;
    padding: 0;
    outline: none;
}

.dropdown-content {
    display: none;
    position: absolute;
    background-color: rgba(15, 10, 30, 0.95);
    min-width: 150px;
    box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.8);
    z-index: 100;
    border: 1px solid rgba(140, 100, 255, 0.2);
    border-radius: 8px;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    padding: 8px 0;
    margin-top: 10px;
}

.dropdown-content a {
    color: rgba(200, 192, 232, 0.6);
    padding: 10px 16px;
    text-decoration: none;
    display: block;
    font-size: 0.75rem;
    text-align: center;
    transition: all 0.3s;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.dropdown-content a:hover, .dropdown-content a.active {
    background-color: rgba(140, 100, 255, 0.15);
    color: #e8e0ff;
}

.dropdown:hover .dropdown-content {
    display: block;
}
"""

with open('style.css', 'r', encoding='utf-8') as f:
    style_content = f.read()

if '.dropdown-content' not in style_content:
    with open('style.css', 'a', encoding='utf-8') as f:
        f.write(css_to_add)

# Update HTML files
nav_pattern = re.compile(r'<nav class="top-nav">.*?</nav>', re.DOTALL)

def get_nav_html(active_page):
    # Determine which dropdown items are active
    portfolio_active = ' active' if active_page in ['projects.html', 'publications.html', 'workshops.html'] else ''
    
    html = '<nav class="top-nav">\n'
    html += f'            <a href="graph.html" class="nav-link{" active" if active_page == "graph.html" else ""}">Graph</a>\n'
    html += f'            <a href="graph.html#bio-section" class="nav-link{" active" if active_page == "bio.html" else ""}">Bio</a>\n'
    html += f'            <a href="skills.html" class="nav-link{" active" if active_page == "skills.html" else ""}">Skills</a>\n'
    html += f'            <a href="experience.html" class="nav-link{" active" if active_page == "experience.html" else ""}">Experience</a>\n'
    html += f'            <a href="education.html" class="nav-link{" active" if active_page == "education.html" else ""}">Education</a>\n'
    
    html += f"""            <div class="dropdown">
                <button class="dropbtn nav-link{portfolio_active}">Portfolio ▾</button>
                <div class="dropdown-content">
                    <a href="projects.html" class="{"active" if active_page == "projects.html" else ""}">Projects</a>
                    <a href="publications.html" class="{"active" if active_page == "publications.html" else ""}">Publications</a>
                    <a href="workshops.html" class="{"active" if active_page == "workshops.html" else ""}">Workshops</a>
                </div>
            </div>\n"""
            
    html += f'            <a href="contact.html" class="nav-link{" active" if active_page == "contact.html" else ""}">Contact</a>\n'
    html += '        </nav>'
    return html

# 'bio.html' actually maps to index.html#bio-section now, but graph.html is where the bio lives right now
# Wait, graph.html has the Bio section. So if file is graph.html, we check if it had bio active originally?
# Actually, graph.html has active on Bio originally.

files = glob.glob('*.html')
for file in files:
    if file == 'index.html': continue # landing page has no top-nav
    
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if there's a nav
    if '<nav class="top-nav">' in content:
        # Determine pseudo active page for bio mapping
        active_page = file
        if file == 'graph.html':
            active_page = 'bio.html' # Because in graph.html, we want Bio to be highlighted
            
        new_nav = get_nav_html(active_page)
        new_content = nav_pattern.sub(new_nav, content)
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)

print("Navigation updated successfully.")
