import pytest


@pytest.fixture(autouse=True)
def plain_static_storage(settings):
    """Tests render pages with DEBUG=False; the hashed manifest storage would need `collectstatic` first."""
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
