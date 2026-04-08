import os

bind = "0.0.0.0:5000"
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
threads = 4
timeout = 60
graceful_timeout = 20
accesslog = "-"
errorlog = "-"
