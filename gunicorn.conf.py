import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = 3
timeout = 60
accesslog = "-"
errorlog = "-"
