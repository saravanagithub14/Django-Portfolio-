"""
Pixel icons (Pixelarticons, plus four drawn for the site) for the content pages, replacing the
emoji the site used to show. Path data and licence notes: icons_data.py.

Icon fields on the content models (Project.emoji, Degree.icon, Strength.icon, ...) hold an icon
name such as "microscope". Templates render them with the `icon` filter / tag from
portfolio_extras: `{{ item.icon|icon }}` or `{% icon "mail" %}`.

Anything that isn't a known name still renders: a legacy emoji maps through EMOJI_TO_ICON, and
unknown text falls back to a neutral dot, so an admin typo never breaks a page.
"""
import re

from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .icons_data import ICONS

FALLBACK = "circle-dot"

# Emoji the site used to store, mapped to the closest icon
EMOJI_TO_ICON = {
    "🧠": "brain", "🤖": "bot", "🔮": "cpu", "📊": "chart-column", "🔬": "microscope", "🧬": "dna",
    "🌿": "leaf", "🎖": "award", "🏆": "award", "🕸": "network", "⚔": "layers", "📜": "scroll-text",
    "🛠": "wrench", "📚": "book-open", "🎓": "graduation-cap", "🖼": "image", "🏛": "landmark",
    "🚀": "rocket", "✉": "mail", "📧": "mail", "🎤": "mic", "🧪": "flask-conical", "⚙": "settings",
    "👁": "eye", "🌐": "globe", "🤝": "handshake", "🔍": "search", "💻": "laptop", "🐍": "code-xml",
    "💼": "briefcase", "✍": "pen-line", "💬": "message-circle", "📸": "camera", "📷": "camera",
    "📍": "map-pin", "📄": "file-text", "📖": "book-open", "📝": "notebook-pen", "🎥": "video",
    "🎬": "clapperboard", "❤": "heart", "⭐": "star", "🦺": "hard-hat", "🏥": "scan",
}

# Icons used by the page chrome only (navbar etc.); not offered for content in admin
UI_ICONS = {"menu"}
ICON_NAMES = sorted(name for name in ICONS if name not in UI_ICONS)

# Variation selectors and joiners that follow many emoji ("🛠️" is "🛠" + U+FE0F)
_EMOJI_MODIFIERS = re.compile(r"[\uFE0E\uFE0F\u200D]")


def icon_name(value):
    """Resolve an icon name or legacy emoji to a known icon name."""
    value = (value or "").strip()
    if value in ICONS:
        return value
    value = _EMOJI_MODIFIERS.sub("", value)
    return EMOJI_TO_ICON.get(value, FALLBACK)


def render_icon(value, css_class=""):
    """Inline SVG for an icon name (or legacy emoji). Decorative: hidden from screen readers.
    crispEdges keeps the pixel squares sharp instead of anti-aliasing their edges."""
    name = icon_name(value)
    classes = f"ico ico-{name} {css_class}".strip()
    return format_html(
        '<svg class="{}" viewBox="0 0 24 24" fill="currentColor" shape-rendering="crispEdges" '
        'aria-hidden="true" focusable="false">{}</svg>',
        classes, mark_safe(ICONS[name]),
    )


ICON_HELP_TEXT = "Icon name, e.g. microscope, brain, mail. Available: " + ", ".join(ICON_NAMES)
