import pytest

from chatbot.apps import should_warm_up


@pytest.mark.parametrize("argv, environ, expected", [
    (["/venv/bin/gunicorn", "portfolio_hub.wsgi"], {}, True),
    (["/venv/bin/gunicorn", "--preload", "portfolio_hub.wsgi"], {}, False),
    (["/venv/bin/gunicorn", "portfolio_hub.wsgi"], {"RAG_WARM_UP": "0"}, False),
    (["manage.py", "runserver"], {"RUN_MAIN": "true"}, True),
    (["manage.py", "runserver"], {}, False),  # the autoreloader's watcher process
    (["manage.py", "migrate"], {"RUN_MAIN": "true"}, False),
    (["manage.py", "build_rag_index"], {}, False),
    (["/venv/bin/pytest"], {}, False),
])
def test_should_warm_up(argv, environ, expected):
    assert should_warm_up(argv, environ) is expected
