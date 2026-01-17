from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name='development'):
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Load configuration
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # CORS Configuration - UPDATED
    if config_name == 'production':
        # Production: Only allow specific origins
        CORS(app, 
             origins=app.config.get('CORS_ORIGINS', ['*']),
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    else:
        # Development: Allow all
        CORS(app)
    
    # Initialize storage service
    from app.services.storage import init_storage_service
    init_storage_service(app)
    
    # Register blueprints
    from app.routes.upload import upload_bp
    from app.routes.jobs import jobs_bp
    
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(jobs_bp, url_prefix='/api')
    
    # Import models
    from app.models import Document, ProcessingJob, JobResult
    
    return app