import os

bind = f"0.0.0.0:{os.getenv('PORT', os.getenv('AUTOOPS_PORT', '5000'))}"
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
threads = 4
timeout = 60
graceful_timeout = 20
accesslog = "-"
errorlog = "-"
