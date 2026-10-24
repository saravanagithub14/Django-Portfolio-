"""
Gunicorn settings, read automatically from the working directory (Render and EC2 both start gunicorn here).
Flags on the command line still win over these.

One process with threads: every worker process loads the chatbot's ONNX models (~375MB, see CLAUDE.md), so
two workers don't fit Render free's 512MB. Threads share one copy of the models and keep serving pages
while a chat is answered.

gthread workers also fix the timeout: a sync worker is killed when one request passes `timeout`, and a
cold first chat (model load + router + rerank + answer) can pass gunicorn's default 30s on Render's CPU.
With gthread, `timeout` only covers a stuck worker process, not a slow request.
"""
import os

workers = int(os.getenv("GUNICORN_WORKERS", "1"))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
