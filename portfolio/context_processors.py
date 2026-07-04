import os
import json
from pathlib import Path
from django.conf import settings
from portfolio.models import UserProfile

BASE_DIR = Path(settings.BASE_DIR)

def load_fallback_json(filename):
    """Load JSON from the fallback files under users/default/data/."""
    filepath = BASE_DIR / 'users' / 'default' / 'data' / filename
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading fallback JSON {filename}: {e}")
    return {}

def portfolio_context(request):
    """
    Exposes 'config' and 'bio' structures to all templates.
    Checks the database first, and falls back to JSON files if empty or not migrated.
    """
    context = {
        'config': {},
        'bio': {},
        'active_page': '',
    }

    # Determine current active page based on path
    path = request.path.strip('/')
    if not path or path == 'index.html':
        context['active_page'] = 'home'
    else:
        # Match e.g. 'bio' or 'bio.html' -> 'bio'
        page_name = path.split('.')[0]
        context['active_page'] = page_name

    try:
        # Try to get the first profile in the database
        profile = UserProfile.objects.select_related('bio_section').first()
        
        if profile:
            # Reconstruct the config dictionary to match what the old template expects
            social = {
                'email': profile.email,
                'github': profile.github,
                'github_handle': profile.github_handle,
                'linkedin': profile.linkedin,
                'linkedin_handle': profile.linkedin_handle,
                'medium': profile.medium,
                'medium_handle': profile.medium_handle,
                'whatsapp': profile.whatsapp,
                'whatsapp_number': profile.whatsapp_number,
                'instagram': profile.instagram,
                'instagram_handle': profile.instagram_handle,
                'orcid': profile.orcid,
                'researchgate': profile.researchgate,
                'location': profile.location,
                'resume_url': profile.resume_url,
            }
            
            chat_widget_config = {
                'enabled': False,
                'api_url': '/chatbot/api/chat/',
                'bot_name': 'Saravana\'s AI',
            }
            # Retrieve chatbot config from chatbot app dynamically if imported
            try:
                from chatbot.models import Chatbot
                bot = Chatbot.objects.filter(enabled=True).first()
                if bot:
                    chat_widget_config['enabled'] = True
                    chat_widget_config['bot_name'] = bot.bot_name
            except Exception:
                pass

            metrics = [{'value': m.value, 'label': m.label} for m in profile.metrics.all()]
            roles = [r.name for r in profile.roles.all()]
            
            # Format navigation
            navigation = []
            top_level_navs = profile.navigation_items.filter(parent=None)
            for item in top_level_navs:
                if item.dropdown:
                    navigation.append({
                        'label': item.label,
                        'id': item.active_id,
                        'dropdown': True,
                        'children': [{'label': c.label, 'url': c.url, 'id': c.active_id} for c in item.children.all()]
                    })
                else:
                    navigation.append({
                        'label': item.label,
                        'url': item.url,
                        'id': item.active_id
                    })

            context['config'] = {
                'site_title': profile.site_title,
                'site_description': profile.site_description,
                'tagline': profile.tagline,
                'tagline_sub': profile.tagline_sub,
                'profile_image': profile.profile_image,
                'roles': roles,
                'intro': profile.intro,
                'metrics': metrics,
                'social': social,
                'chat_widget': chat_widget_config,
                'navigation': navigation,
                'landing_quote': profile.landing_quote,
                'landing_highlight': profile.landing_highlight,
                'landing_author': profile.landing_author,
                'landing_welcome': profile.landing_welcome,
            }

            # Reconstruct the bio dictionary
            bio_sec = getattr(profile, 'bio_section', None)
            if bio_sec:
                paragraphs = [p.text for p in bio_sec.paragraphs.all()]
                strengths = [{'icon': s.icon, 'title': s.title, 'description': s.description} for s in bio_sec.strengths.all()]
                explore_grid = [{'icon': g.icon, 'title': g.title, 'desc': g.desc, 'url': g.url} for g in bio_sec.explore_grid.all()]
                
                context['bio'] = {
                    'journey': {
                        'label': bio_sec.journey_label,
                        'title': bio_sec.journey_title,
                        'paragraphs': paragraphs
                    },
                    'strengths': {
                        'label': 'What Makes Me Different',
                        'title': 'Scientific Rigor Meets AI Engineering',
                        'entries': strengths
                    },
                    'teaching': {
                        'label': bio_sec.teaching_label,
                        'title': bio_sec.teaching_title,
                        'description': bio_sec.teaching_description
                    },
                    'explore_grid': explore_grid
                }
            
            return context

    except Exception as e:
        # DB tables don't exist yet, fallback to JSON files
        print(f"Database error in context processor, falling back to JSON config: {e}")

    # Fallback loading
    fallback_config = load_fallback_json('config.json')
    fallback_bio = load_fallback_json('bio.json')

    # Fix chat widget api url to point to django chatbot endpoint if fallback is used
    if 'chat_widget' in fallback_config:
        fallback_config['chat_widget']['api_url'] = '/chatbot/api/chat/'

    context['config'] = fallback_config
    context['bio'] = fallback_bio
    return context
