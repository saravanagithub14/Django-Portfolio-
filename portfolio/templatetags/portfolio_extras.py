import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def tojson(value):
    """Safely convert a Python object to JSON string for JavaScript."""
    try:
        return mark_safe(json.dumps(value))
    except Exception:
        return mark_safe("[]")

@register.filter
def capitalize(value):
    """Capitalize a string."""
    if isinstance(value, str):
        return value.capitalize()
    return value

@register.filter
def is_dropdown_active(dropdown_item, active_page):
    """
    Checks if any child in a dropdown item's children list matches the active page.
    This replaces Jinja2 template namespace setting in navbar.
    """
    if not dropdown_item or not active_page:
        return False
        
    # Standard navigation JSON data: children is a list of dicts.
    # In database model: it will be a Django queryset of child items.
    children = []
    if hasattr(dropdown_item, 'children'):
        # If it's a Django model object, retrieve the children relation
        children = dropdown_item.children.all()
    elif isinstance(dropdown_item, dict) and 'children' in dropdown_item:
        # If it's a dictionary (from JSON load fallback)
        children = dropdown_item['children']
        
    for child in children:
        child_id = ""
        if isinstance(child, dict):
            child_id = child.get('id', '')
        elif hasattr(child, 'active_id'):
            child_id = child.active_id
            
        if child_id == active_page:
            return True
            
    return False
