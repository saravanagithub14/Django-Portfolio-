"""What the site sends through Cloudflare (see cloudflare.md)."""
import json
import re

import pytest
from django.contrib.auth.models import User

from portfolio.models import UserProfile
from portfolio.urls import urlpatterns

pytestmark = pytest.mark.django_db

PUBLIC_PAGES = ["/", "/bio/", "/skills/", "/experience/", "/education/", "/projects/", "/publications/", "/workshops/",
                "/summary/", "/contact/", "/languages/", "/gallery/", "/blogs/", "/graph/", "/projects.html"]


@pytest.fixture
def owner():
    user = User.objects.create_superuser("owner", "owner@example.com", "a-strong-test-password")
    UserProfile.objects.create(user=user, site_title="Saravana Perumal R.", email="me@example.com")
    return user


@pytest.fixture
def edge_cache(settings):
    settings.EDGE_CACHE_SECONDS = 300


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_public_pages_can_be_cached_at_the_edge(client, owner, edge_cache, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response["Cache-Control"] == "public, max-age=0, s-maxage=300"
    assert not response.cookies, "Cloudflare won't cache a response that sets a cookie"
    assert "Cookie" not in response.get("Vary", "")


def test_the_list_above_covers_every_page():
    clean_urls = {"/" + str(p.pattern) for p in urlpatterns if not str(p.pattern).endswith(".html")}
    assert clean_urls == {p for p in PUBLIC_PAGES if not p.endswith(".html")}


def test_edge_caching_is_off_by_default(client, owner):
    assert "Cache-Control" not in client.get("/bio/")


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_a_signed_in_owner_gets_the_same_page_as_a_visitor(client, owner, edge_cache, path):
    """The edge serves one copy to everyone, so nothing on these pages may depend on who is asking."""
    anonymous = client.get(path).content
    client.force_login(owner)
    assert client.get(path).content == anonymous


def test_other_responses_stay_out_of_the_edge_cache(client, owner, edge_cache):
    assert "s-maxage" not in client.get("/admin/login/").get("Cache-Control", "")
    assert "s-maxage" not in client.get("/login/").get("Cache-Control", "")
    assert "s-maxage" not in client.get("/no-such-page/").get("Cache-Control", "")
    client.force_login(owner)
    assert "s-maxage" not in client.get("/admin/").get("Cache-Control", "")


def test_public_links_use_site_url(client, owner, settings):
    settings.SITE_URL = "https://portfolio.example"
    html = client.get("/experience/").content.decode()
    assert '<link rel="canonical" href="https://portfolio.example/experience">' in html
    assert 'og:image" content="https://portfolio.example/static/images/profile.jpg"' in html
    assert "vercel.app" not in html


@pytest.mark.parametrize("path, items", [("/experience/", 2), ("/projects/", 2), ("/graph/", None)])
def test_structured_data_is_valid_json(client, owner, path, items):
    html = client.get(path).content.decode()
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    data = json.loads(block)
    if items:
        assert len(data["itemListElement"]) == items
        assert data["itemListElement"][-1]["item"].endswith(".html")
