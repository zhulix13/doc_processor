web: gunicorn run:app
worker: celery -A celery_worker.celery worker --pool=prefork --loglevel=info