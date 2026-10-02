from django.template import Context, Template

from portfolio.icons import FALLBACK, ICON_NAMES, icon_name, render_icon


def test_names_emoji_and_unknown_values_resolve():
    assert icon_name("microscope") == "microscope"
    assert icon_name("🔬") == "microscope"
    assert icon_name("🛠️") == "wrench"  # emoji + variation selector
    assert icon_name("not-an-icon") == FALLBACK
    assert icon_name("") == FALLBACK
    assert FALLBACK in ICON_NAMES


def test_render_is_decorative_crisp_pixel_svg():
    svg = render_icon("mail")
    assert svg.startswith('<svg class="ico ico-mail"')
    assert 'aria-hidden="true"' in svg and 'fill="currentColor"' in svg
    assert 'shape-rendering="crispEdges"' in svg


def test_every_icon_has_drawing_and_ui_icons_stay_out_of_admin():
    from portfolio.icons_data import CUSTOM_ICONS, ICONS, SOURCE
    assert set(SOURCE) == set(ICONS)
    for name in CUSTOM_ICONS:  # drawn for the site on the same 24-grid
        assert SOURCE[name] == "custom" and "M" in ICONS[name]
    assert "menu" in ICONS and "menu" not in ICON_NAMES


def test_template_filter_and_tag():
    html = Template('{% load portfolio_extras %}{{ value|icon }}{% icon "brain" %}').render(Context({"value": "📊"}))
    assert "ico-chart-column" in html and "ico-brain" in html
    assert "📊" not in html
