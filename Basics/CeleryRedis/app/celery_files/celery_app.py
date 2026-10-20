# celery_app.py

from celery import Celery

celery_app = Celery(
    "todo_app",
    broker="redis://localhost:6379/0",#Where Celery puts tasks waiting for a worker.
    backend="redis://localhost:6379/1", #Where Celery can store task results/status.
    include=["app.celery_files.tasks"]#tell the worker where the tasks are
)

