"""
Celery runner
"""
from tasks import app as celery_app

if __name__ == "__main__":
    celery_app.worker_main(
        argv=[
            "celery",
            "-A",
            "tasks",
            "worker",
            "--loglevel=info",
            "--concurrency=2",   # adjust to CPU cores
        ]
    )
