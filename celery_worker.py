import os
from celery import Celery
from app import create_app, db

# Get environment
config_name = os.getenv('FLASK_ENV', 'development')

# Create Flask app context
flask_app = create_app(config_name)

# Create Celery instance
celery = Celery(
    'document_processor',
    broker=flask_app.config['CELERY_BROKER_URL'],
    backend=flask_app.config['CELERY_RESULT_BACKEND']
)

# Update config
celery.conf.update(
    flask_app.config,
    # Redis-specific settings
    broker_connection_retry_on_startup=True,
    result_backend_transport_options={'master_name': 'mymaster'},
)

# Make sure Flask app context is available in tasks
class ContextTask(celery.Task):
    """Make celery tasks work with Flask app context"""
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)

celery.Task = ContextTask

# Import tasks so Celery can discover them
from app.tasks.processing_tasks import extract_data_task

# For debugging
if __name__ == '__main__':
    celery.start()