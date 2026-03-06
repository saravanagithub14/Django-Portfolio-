import os
import re

nav_css = """        /* Navigation */
        .top-nav {
            width: 100%;
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 15px;
            margin-bottom: 40px;
            padding: 10px 0 20px 0;
            border-bottom: 1px solid rgba(140, 100, 255, 0.2);
            animation: fadeUp 0.6s ease forwards;
        }

        .nav-link {
            color: rgba(200, 192, 232, 0.6);
            text-decoration: none;
            font-size: 0.8rem;
            letter-spacing: 1px;
            text-transform: uppercase;
            transition: color 0.3s, transform 0.3s;
        }

        .nav-link:hover, .nav-link.active {
            color: #e8e0ff;
            transform: translateY(-2px);
        }"""

def get_nav_html(current_page):
    pages = [
        ('index.html', 'Graph'),
        ('bio.html', 'Bio'),
        ('skills.html', 'Skills'),
        ('experience.html', 'Experience'),
        ('education.html', 'Education'),
        ('projects.html', 'Projects'),
        ('publications.html', 'Publications'),
        ('workshops.html', 'Workshops'),
        ('contact.html', 'Contact')
    ]
    
    links = []
    for href, label in pages:
        active_class = ' active' if href == current_page else ''
        links.append(f'            <a href="{href}" class="nav-link{active_class}">{label}</a>')
    
    links_str = '\n'.join(links)
    return f"""        <nav class="top-nav">
{links_str}
        </nav>"""

files = ['bio.html', 'skills.html', 'experience.html', 'education.html', 'projects.html', 'publications.html', 'workshops.html', 'contact.html', 'summary.html']

for f in files:
    if not os.path.exists(f): 
        continue
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()

    # Find the CSS back-btn block and replace with nav_css
    # We want to replace from '.back-btn {' to '} }' etc, basically the whole block.
    # The back-btn usually has:
    # .back-btn { ... }
    # .back-btn:hover { ... }
    # .back-btn svg { ... }
    # .back-btn:hover svg { ... }
    # Let's replace the block containing these.
    
    # regex for .back-btn to the end of .back-btn:hover svg { ... }
    css_pattern = re.compile(r'(\s*/\*\s*Back(\s*btn)?\s*\*/\s*)?\.back-btn\s*\{.*?(?:\.back-btn:hover\s+svg\s*\{.*?\})', re.DOTALL)
    
    # Now for HTML replacement
    # <a href="index.html" class="back-btn">
    # ...
    # </a>
    html_pattern = re.compile(r'<a\s+href="index\.html"\s+class="back-btn".*?</a\>', re.DOTALL)

    new_content = css_pattern.sub(nav_css, content)
    new_content = html_pattern.sub(get_nav_html(f), new_content)
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    # if it didn't change what we wanted, maybe css wasn't found due to different structure.
    print(f'Processed {f}')
