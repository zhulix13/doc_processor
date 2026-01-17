import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration - shared across all environments"""
    
    # Flask Core
    SECRET_KEY = os.getenv('SECRET_KEY', 'dona@hotboy123')
    
    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # Celery - UPDATED to use Redis
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')
    
    # MinIO/R2
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
    MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'documents')
    MINIO_SECURE = os.getenv('MINIO_SECURE', 'True').lower() == 'true'
    
    # Upload Settings
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf,docx,xlsx,csv,jpg,png').split(','))
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'tmp/uploads')
    
    # Job Types
    VALID_JOB_TYPES = [
        'extract_data',
        'convert_to_pdf',
        'convert_to_excel',
        'convert_to_csv',
        'ocr_document',
    ]
    
    # Result Types
    VALID_RESULT_TYPES = [
        'extracted_text',
        'extracted_tables',
        'extracted_images',
        'document_metadata',
        'output_pdf',
        'output_excel',
        'output_csv',
        'ocr_results',
    ]


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False
    
    # Stricter settings for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'echo': False,
    }
    
    # Production CORS - UPDATE with your frontend URL
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')


class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:password@localhost:5432/doc_processor_test'


# Config dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}