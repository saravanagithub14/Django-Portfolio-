from django.contrib.staticfiles import finders
from django.shortcuts import render
from django.templatetags.static import static
from portfolio.models import (
    UserProfile, SkillCategory, ProjectPage, ExperiencePage, EducationPage,
    PublicationsPage, WorkshopsPage, FocusPage, LanguagePage, GalleryPage, BlogPage
)
from portfolio.graph import build_graph


# --- Helper to serialize Graph Nodes ---
def get_graph_data():
    # Built from the content models on each request, so admin edits show up in the graph immediately
    try:
        graph = build_graph()
        if graph:
            return graph
    except Exception:
        pass
    return {"id": "root", "name": "Portfolio", "type": "root"}

# --- Views ---

def index_view(request):
    return render(request, 'pages/index.html', {'graph_data': get_graph_data()})

def graph_view(request):
    context = {
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/graph.html', context)

def bio_view(request):
    context = {
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/bio.html', context)

def skills_view(request):
    skills_context = {}
    try:
        profile = UserProfile.objects.first()
        if profile:
            # We look for a skill categories
            cats = SkillCategory.objects.filter(profile=profile)
            if cats.exists():
                groups = []
                for c in cats:
                    groups.append({
                        'id': c.accordion_id,
                        'name': c.name,
                        'active': c.active,
                        'tags': [{'name': s.name, 'highlight': s.highlight, 'tier': s.tier, 'context': s.context} for s in c.skills.all()]
                    })
                skills_context = {
                    'page_label': 'High-Impact Expertise',
                    'page_title': 'Skills & Technologies',
                    'page_sub': 'Organized hierarchy for cognitive clarity. Use the accordions to explore specific technical stacks.',
                    'accordion_groups': groups
                }
    except Exception:
        pass


    context = {
        'skills': skills_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/skills.html', context)

def experience_view(request):
    exp_context = {}
    try:
        page = ExperiencePage.objects.first()
        if page:
            sections = []
            for sec in page.sections.all():
                jobs = []
                for j in sec.jobs.all():
                    jobs.append({
                        'title': j.title,
                        'company': j.company,
                        'period': j.period,
                        'description': j.description,
                        'tags': j.tag_list
                    })
                sections.append({
                    'heading': sec.heading,
                    'jobs': jobs
                })
            exp_context = {
                'page_label': page.page_label,
                'page_title': page.page_title,
                'page_sub': page.page_sub,
                'sections': sections
            }
    except Exception:
        pass


    context = {
        'experience': exp_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/experience.html', context)

def education_view(request):
    edu_context = {}
    try:
        page = EducationPage.objects.first()
        if page:
            degrees = [{'icon': d.icon, 'degree': d.degree, 'school': d.school, 'year': d.year, 'detail': d.detail} for d in page.degrees.all()]
            certs = [{'badge': c.badge, 'name': c.name, 'detail': c.detail} for c in page.certifications.all()]
            edu_context = {
                'page_label': page.page_label,
                'page_title': page.page_title,
                'page_sub': page.page_sub,
                'degrees': degrees,
                'certifications': certs
            }
    except Exception:
        pass


    context = {
        'education': edu_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/education.html', context)

def projects_view(request):
    proj_context = {}
    try:
        page = ProjectPage.objects.first()
        if page:
            featured_entries = []
            for p in page.projects.filter(featured=True):
                featured_entries.append({
                    'emoji': p.emoji,
                    'title': p.title,
                    'description': p.description,
                    'tags': p.tag_list,
                    'github_url': p.github_url,
                    'demo_url': p.demo_url
                })
            
            categories = []
            for cat in page.categories.all():
                entries = []
                for p in cat.projects.all():
                    entries.append({
                        'name': p.title,
                        'desc': p.description,
                        'url': p.github_url
                    })
                categories.append({
                    'heading': cat.heading,
                    'entries': entries
                })
            
            proj_context = {
                'page_label': page.page_label,
                'page_title': page.page_title,
                'page_sub': page.page_sub,
                'featured': {
                    'heading': page.featured_heading,
                    'entries': featured_entries
                },
                'categories': categories
            }
    except Exception:
        pass


    context = {
        'projects': proj_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/projects.html', context)

def _publication_dict(pub, default_label, icon):
    image = pub.image
    if image and not image.startswith(('http://', 'https://', '/')):
        # A static path; a missing file would raise under the manifest storage, so it's dropped instead
        image = static(image) if finders.find(image) else ''
    doi_url = f'https://doi.org/{pub.doi}' if pub.doi else ''
    return {
        'title': pub.title,
        'meta': pub.meta,
        'label': pub.label or default_label,
        'year': pub.year,
        'summary': pub.summary,
        'tags': pub.tag_list,
        'image': image,
        'icon': icon,
        'doi': pub.doi,
        'doi_url': doi_url,
        'paper_url': pub.paper_url or doi_url,
        'pdf_url': pub.pdf_url,
    }


def publications_view(request):
    pub_context = {}
    try:
        page = PublicationsPage.objects.first()
        if page:
            chapters = [_publication_dict(c, 'Book Chapter', 'book-open') for c in page.book_chapters.all()]
            articles = [_publication_dict(a, 'Research Article', 'flask-conical') for a in page.research_articles.all()]
            # One list, newest first; publications without a year go last
            items = sorted(articles + chapters, key=lambda p: -(p['year'] or 0))
            topics = []
            for item in items:
                topics += [t for t in item['tags'] if t not in topics]
            achievements = [{'icon': ac.icon, 'title': ac.title, 'description': ac.description} for ac in page.achievements.all()]
            pub_context = {
                'page_label': page.page_label,
                'page_title': page.page_title,
                'page_sub': page.page_sub,
                'book_chapters': chapters,
                'research_articles': articles,
                'items': items,
                'topics': topics,
                'achievements': achievements
            }
    except Exception:
        pass


    context = {
        'publications': pub_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/publications.html', context)

def workshops_view(request):
    ws_context = {}
    try:
        page = WorkshopsPage.objects.first()
        if page:
            workshops = [{'icon': w.icon, 'title': w.title, 'description': w.description} for w in page.workshops.all()]
            seminars = [{'icon': s.icon, 'title': s.title, 'description': s.description} for s in page.seminars.all()]
            ws_context = {
                'page_label': page.page_label,
                'page_title': page.page_title,
                'page_sub': page.page_sub,
                'workshops': workshops,
                'seminars': seminars
            }
    except Exception:
        pass


    context = {
        'workshops': ws_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/workshops.html', context)

def summary_view(request):
    focus_context = {}
    try:
        page = FocusPage.objects.first()
        if page:
            cards = [{'icon': c.icon, 'title': c.title, 'description': c.description} for c in page.cards.all()]
            entries = [e.text for e in page.positioning_entries.all()]
            focus_context = {
                'page_label': page.page_label,
                'page_title': page.page_title,
                'page_sub': page.page_sub,
                'cards': cards,
                'positioning': {
                    'entries': entries,
                    'tagline': page.positioning_tagline
                }
            }
    except Exception:
        pass


    context = {
        'focus': focus_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/summary.html', context)

def contact_view(request):
    context = {
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/contact.html', context)

def languages_view(request):
    lang_context = {}
    try:
        page = LanguagePage.objects.first()
        if page:
            spoken = [{'name': s.name, 'proficiency': s.proficiency, 'level': s.level} for s in page.spoken.all()]
            programming = [{'name': p.name, 'proficiency': p.proficiency, 'level': p.level} for p in page.programming.all()]
            lang_context = {
                'spoken': spoken,
                'programming': programming
            }
    except Exception:
        pass


    context = {
        'languages': lang_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/languages.html', context)

def _video_dict(title, description, embed_url, category, duration):
    # YouTube embed URLs look like https://www.youtube.com/embed/<id>?start=...; the id gives the thumbnail
    video_id = embed_url.split('/embed/')[-1].split('?')[0] if '/embed/' in embed_url else ''
    return {
        'title': title,
        'description': description,
        'embed_url': embed_url,
        'category': category,
        'duration': duration,
        'thumbnail': f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg' if video_id else '',
        'watch_url': f'https://www.youtube.com/watch?v={video_id}' if video_id else embed_url,
    }


def gallery_view(request):
    gallery_context = {}
    try:
        page = GalleryPage.objects.first()
        if page:
            # Covers come from `manage.py fetch_reel_thumbnails`; a reel without one falls back to the bare embed
            reels = [{
                'title': r.title, 'reel_url': r.reel_url, 'reel_id': r.reel_id,
                'thumbnail': f'img/reels/{r.reel_id}.jpg' if finders.find(f'img/reels/{r.reel_id}.jpg') else '',
            } for r in page.reels.all()]
            videos = [_video_dict(v.title, v.description, v.embed_url, v.category, v.duration) for v in page.videos.all()]
            # The featured video leads the playlist; the template plays the first entry
            if page.featured_embed_url:
                videos.insert(0, _video_dict(
                    page.featured_title, page.featured_description, page.featured_embed_url,
                    page.featured_category, page.featured_duration,
                ))
            gallery_context = {
                'page_label': page.page_label,
                'page_title': page.page_title,
                'page_sub': page.page_sub,
                'reels': reels,
                'videos': videos
            }
    except Exception:
        pass


    context = {
        'gallery': gallery_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/gallery.html', context)

def blogs_view(request):
    blogs_context = {}
    try:
        page = BlogPage.objects.first()
        if page:
            posts = []
            for p in page.posts.all():
                posts.append({
                    'title': p.title,
                    'excerpt': p.excerpt,
                    'category': p.category,
                    'date': p.date,
                    'read_time': p.read_time,
                    'emoji': p.emoji,
                    'tags': p.tag_list,
                    'medium_url': p.medium_url
                })
            blogs_context = {
                'page_label': page.page_label,
                'page_title': page.page_title,
                'page_sub': page.page_sub,
                'stats': {
                    'total_posts': page.stats_total_posts,
                    'platform': page.stats_platform,
                    'topics': page.stats_topics
                },
                'posts': posts
            }
    except Exception:
        pass


    context = {
        'blogs': blogs_context,
        'graph_data': get_graph_data()
    }
    return render(request, 'pages/blogs.html', context)
