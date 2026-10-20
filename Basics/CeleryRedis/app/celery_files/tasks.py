# tasks.py

import time

from app.celery_files.celery_app import celery_app

@celery_app.task
def process_todo(todo_id: int):
    print(f"Processing todo {todo_id}")

    # Simulate slow work
    time.sleep(10)

    print(f"Todo {todo_id} processed successfully")

    return {
        "todo_id": todo_id,
        "status": "processed"
    }