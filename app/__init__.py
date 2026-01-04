from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# Initialize extensions (but don't bind to app yet)
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name='development'):
    """
    Application factory pattern.
    Creates and configures the Flask application.
    
    Args:
        config_name: Which config to use ('development', 'production', 'testing')
    
    Returns:
        Flask app instance
    """
    app = Flask(__name__)
    
    # Load configuration
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # Register blueprints (routes)
   #  from app.routes.upload import upload_bp
   #  from app.routes.jobs import jobs_bp
    
   #  app.register_blueprint(upload_bp, url_prefix='/api')
   #  app.register_blueprint(jobs_bp, url_prefix='/api')
    
    # Import models so Flask-Migrate can detect them
    from app.models import Document, ProcessingJob, JobResult
    
    return app