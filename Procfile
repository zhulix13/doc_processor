web: gunicorn run:app
worker: celery -A celery_worker.celery worker --pool=solo --loglevel=info