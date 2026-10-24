import os
import sys
import threading

from django.apps import AppConfig


def should_warm_up(argv=None, environ=None):
    """Warm the RAG models only in a process that serves requests (not tests or other manage.py commands)."""
    argv = sys.argv if argv is None else argv
    environ = os.environ if environ is None else environ
    if environ.get("RAG_WARM_UP", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    program = os.path.basename(argv[0]) if argv else ""
    if "gunicorn" in program:
        # With --preload the app loads in the master before forking; a loading thread there could leave
        # a lock held in the workers, so the first chat loads the models instead
        return "--preload" not in argv
    # runserver's autoreloader runs a watcher parent and a serving child; only the child sets RUN_MAIN
    return len(argv) > 1 and argv[1] == "runserver" and environ.get("RUN_MAIN") == "true"


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatbot"

    def ready(self):
        from django.apps import apps
        from django.db.models.signals import post_delete, post_save

        from chatbot.rag.index import site_changed
        # Admin edits to the site's content reach V.E.R.A.'s index on the next chat
        for model in apps.get_app_config("portfolio").get_models():
            post_save.connect(site_changed, sender=model, dispatch_uid=f"rag-site-save-{model.__name__}")
            post_delete.connect(site_changed, sender=model, dispatch_uid=f"rag-site-delete-{model.__name__}")

        if should_warm_up():
            from chatbot.rag.index import warm_up
            # In the background: the site serves pages while the models load
            threading.Thread(target=warm_up, name="rag-warm-up", daemon=True).start()
