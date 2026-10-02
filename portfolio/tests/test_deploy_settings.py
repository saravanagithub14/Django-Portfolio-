"""Settings needed to run behind nginx on EC2 (see aws.md, Part 0)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]


def settings_with_env(**env):
    """Import the settings module in a fresh process with the given environment."""
    code = (
        "import json, portfolio_hub.settings as s;"
        "print(json.dumps({'db': str(s.DATABASES['default']['NAME']), 'csrf': s.CSRF_TRUSTED_ORIGINS}))"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True,
                            env={**os.environ, **env}, check=True)
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_sqlite_path_and_csrf_origins_come_from_env(tmp_path):
    db = str(tmp_path / "live.sqlite3")
    values = settings_with_env(SQLITE_PATH=db, CSRF_TRUSTED_ORIGINS="https://a.example,https://www.a.example")
    assert values["db"] == db
    assert values["csrf"][-2:] == ["https://a.example", "https://www.a.example"]
    assert "https://*.onrender.com" in values["csrf"], "Render keeps working"


def test_defaults_without_env():
    values = settings_with_env(SQLITE_PATH="", CSRF_TRUSTED_ORIGINS="")
    assert values["db"].endswith("db.sqlite3")
    assert "https://*.onrender.com" in values["csrf"]


@pytest.mark.django_db
def test_admin_login_over_https_behind_proxy():
    """nginx terminates HTTPS and forwards X-Forwarded-Proto; the CSRF origin check must accept it."""
    User.objects.create_superuser("owner", "o@example.com", "a-strong-test-password")
    client = Client(enforce_csrf_checks=True)
    proxy = {"HTTP_HOST": "portfolio.example", "HTTP_X_FORWARDED_PROTO": "https"}

    client.get("/admin/login/", **proxy)
    token = client.cookies["csrftoken"].value
    response = client.post("/admin/login/?next=/admin/", {
        "username": "owner", "password": "a-strong-test-password", "csrfmiddlewaretoken": token,
    }, HTTP_ORIGIN="https://portfolio.example", HTTP_REFERER="https://portfolio.example/admin/login/", **proxy)

    assert response.status_code == 302, response.content[:300]
    assert response["Location"] == "/admin/"
