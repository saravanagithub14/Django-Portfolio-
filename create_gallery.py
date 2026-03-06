import glob
import re
import shutil

# First, create the gallery.html file by copying an existing template like workshops.html
shutil.copy('workshops.html', 'gallery.html')

with open('gallery.html', 'r', encoding='utf-8') as f:
    gallery_content = f.read()

# Replace titles and descriptions
gallery_content = gallery_content.replace('<title>Workshops & Talks — Saravana Perumal R.</title>', '<title>Gallery — Saravana Perumal R.</title>')
gallery_content = gallery_content.replace('Technical workshops, guest lectures, and corporate training sessions.', 'A collection of featured video presentations and content.')
gallery_content = gallery_content.replace('<div class="page-label">Speaking & Training</div>', '<div class="page-label">Media & Presentations</div>')
gallery_content = gallery_content.replace('<h1 class="page-title">Workshops & Talks</h1>', '<h1 class="page-title">Video Gallery</h1>')
gallery_content = gallery_content.replace('<p class="page-sub">From university guest lectures to corporate technical training — sharing knowledge on AI, ML, and Next-Gen Tech.</p>', '<p class="page-sub">Featured video content, talks, and showcases.</p>')

# Replace the content blocks with the videos
video_html = """
        <div class="project-card" style="margin-bottom: 40px; padding: 20px; text-align: center;">
            <h2 class="project-title" style="margin-bottom: 20px;">Featured Video 1</h2>
            <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
                <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;" src="https://www.youtube.com/embed/iCSkyJWMhrU" title="YouTube video player" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
            </div>
        </div>

        <div class="project-card" style="margin-bottom: 40px; padding: 20px; text-align: center;">
            <h2 class="project-title" style="margin-bottom: 20px;">Featured Video 2</h2>
            <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
                <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;" src="https://www.youtube.com/embed/a29OinkSuKk?start=2212" title="YouTube video player" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
            </div>
        </div>
"""

# Extract the content div and replace everything between page-sub and the Back to top button
# Find the start and end of the workshop list
start_marker = '<p class="page-sub">Featured video content, talks, and showcases.</p>'
end_marker = '<!-- Graph View at the bottom -->'
parts = gallery_content.split(end_marker)

if len(parts) > 1:
    sub_parts = parts[0].split(start_marker)
    if len(sub_parts) > 1:
        new_content = sub_parts[0] + start_marker + '\n' + video_html + '\n\n    ' + end_marker + parts[1]
        
        with open('gallery.html', 'w', encoding='utf-8') as f:
            f.write(new_content)


# Update the nav script
nav_pattern = re.compile(r'<nav class="top-nav">.*?</nav>', re.DOTALL)

def get_nav_html(active_page):
    portfolio_active = ' active' if active_page in ['projects.html', 'publications.html', 'workshops.html', 'gallery.html'] else ''
    
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
                    <a href="gallery.html" class="{"active" if active_page == "gallery.html" else ""}">Gallery</a>
                </div>
            </div>\n"""
            
    html += f'            <a href="contact.html" class="nav-link{" active" if active_page == "contact.html" else ""}">Contact</a>\n'
    html += '        </nav>'
    return html


files = glob.glob('*.html')
for file in files:
    if file == 'index.html': continue 
    
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '<nav class="top-nav">' in content:
        active_page = file
        if file == 'graph.html':
            active_page = 'bio.html'
            
        new_nav = get_nav_html(active_page)
        new_content = nav_pattern.sub(new_nav, content)
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)

print("Created gallery.html and updated navigation successfully.")
