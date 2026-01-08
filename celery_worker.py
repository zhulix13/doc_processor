import os
from celery import Celery
from app import create_app, db

# Create Flask app context
flask_app = create_app(os.getenv('FLASK_ENV', 'development'))

# Create Celery instance
celery = Celery(
    'document_processor',
    broker=flask_app.config['CELERY_BROKER_URL'],
    backend=flask_app.config['CELERY_RESULT_BACKEND']
)

# Load Celery config from Flask
celery.conf.update(flask_app.config)

# Make sure Flask app context is available in tasks
class ContextTask(celery.Task):
    """Make celery tasks work with Flask app context"""
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)

celery.Task = ContextTask

# Import tasks so Celery can discover them
from app.tasks import pdf_tasks, excel_tasks, csv_tasks

# For debugging
if __name__ == '__main__':
    celery.start()