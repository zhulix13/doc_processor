from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app import db


class ProcessingJob(db.Model):
    """
    Represents a document processing task.
    
    Each job performs ONE operation (extract_data, convert_to_csv, etc.).
    A single document can have multiple jobs over its lifetime.
    Similar to how one Stripe customer can have multiple subscriptions.
    """
    __tablename__ = 'processing_jobs'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key - Every job belongs to a document
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False)
    
    # Job Configuration
    job_type = Column(String(50), nullable=False)  # extract_data, convert_to_csv, etc.
    status = Column(String(20), nullable=False, default='queued')
    priority = Column(Integer, default=5)  # 1=highest, 5=lowest
    celery_task_id = Column(String(255))  # For tracking/cancelling Celery tasks
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Retry Logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Error Tracking
    error_message = Column(Text)  # User-friendly error message
    error_trace = Column(Text)    # Full stack trace for debugging
    
    # Job-specific Options
    options_ = Column('options', JSONB)  # e.g., {'ocr_language': 'eng', 'dpi': 300}
    
    # Relationships
    document = relationship('Document', back_populates='jobs')
    results = relationship('JobResult', back_populates='job', cascade='all, delete-orphan')
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_jobs_document_id', 'document_id'),
        Index('idx_jobs_status', 'status'),
        Index('idx_jobs_job_type', 'job_type'),
        Index('idx_jobs_created_at', 'created_at'),
        Index('idx_jobs_celery_task_id', 'celery_task_id'),
    )
    
    def __repr__(self):
        return f'<ProcessingJob {self.job_type} ({self.status})>'
    
    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            'id': str(self.id),
            'document_id': str(self.document_id),
            'job_type': self.job_type,
            'status': self.status,
            'priority': self.priority,
            'celery_task_id': self.celery_task_id,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
            'started_at': self.started_at.isoformat() if self.started_at is not None else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at is not None else None,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
            'options': self.options_,
        }