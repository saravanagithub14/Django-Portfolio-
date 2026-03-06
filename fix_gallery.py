import re

with open('gallery.html', 'r', encoding='utf-8') as f:
    c = f.read()

new_html = """<p class="page-sub">Featured video content, talks, and showcases.</p>

        <div class="project-card" style="margin-bottom: 40px; padding: 20px; text-align: center; background: rgba(100, 60, 200, 0.08); border: 1px solid rgba(140, 100, 255, 0.2); border-radius: 16px;">
            <h2 class="project-title" style="margin-bottom: 20px; font-size: 1.5rem; color: #e8e0ff;">AI Workflow for Business Development</h2>
            <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
                <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;" src="https://www.youtube.com/embed/iCSkyJWMhrU" title="YouTube video player" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
            </div>
        </div>

        <div class="project-card" style="margin-bottom: 40px; padding: 20px; text-align: center; background: rgba(100, 60, 200, 0.08); border: 1px solid rgba(140, 100, 255, 0.2); border-radius: 16px;">
            <h2 class="project-title" style="margin-bottom: 20px; font-size: 1.5rem; color: #e8e0ff;">Introduction to Generative AI</h2>
            <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
                <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;" src="https://www.youtube.com/embed/a29OinkSuKk?start=2212" title="YouTube video player" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
            </div>
        </div>

        <!-- Graph View at the bottom -->"""

pattern = re.compile(r'<p class="page-sub">Featured video content, talks, and showcases.</p>.*?<!-- Graph View at the bottom -->', re.DOTALL)
new_c = pattern.sub(new_html, c)

with open('gallery.html', 'w', encoding='utf-8') as f:
    f.write(new_c)

print('Updated gallery html content.')
