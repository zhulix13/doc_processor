from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app import db


class JobResult(db.Model):
    """
    Stores the output/results from a processing job.
    
    A job can produce multiple results:
    - extracted_text: Plain text from document
    - extracted_tables: Tables as JSON
    - output_csv: Generated CSV file (stored in MinIO)
    - document_metadata: Page count, author, etc.
    
    Similar to how one Stripe subscription can have multiple invoices.
    """
    __tablename__ = 'job_results'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Key - Every result belongs to a job
    job_id = Column(UUID(as_uuid=True), ForeignKey('processing_jobs.id'), nullable=False)
    
    # Result Information
    result_type = Column(String(50), nullable=False)  # extracted_text, output_csv, etc.
    
    # Data Storage (one of these will be populated)
    result_data = Column(JSONB)        # For structured data (< 1MB)
    output_file_key = Column(String(500))  # For files in MinIO
    
    # File Metadata (only if output_file_key is set)
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    job = relationship('ProcessingJob', back_populates='results')
    
    # Constraints and Indexes
    __table_args__ = (
        # Indexes for queries
        Index('idx_results_job_id', 'job_id'),
        Index('idx_results_result_type', 'result_type'),
        
        # Prevent duplicate result types per job
        UniqueConstraint('job_id', 'result_type', name='uq_job_result_type'),
        
        # Ensure at least one data field is populated
        CheckConstraint(
            'result_data IS NOT NULL OR output_file_key IS NOT NULL',
            name='ck_result_has_data'
        ),
    )
    
    def __repr__(self):
        return f'<JobResult {self.result_type} for Job {str(self.job_id)[:8]}>'
    
    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            'id': str(self.id),
            'job_id': str(self.job_id),
            'result_type': self.result_type,
            'result_data': self.result_data,
            'output_file_key': self.output_file_key,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'created_at': self.created_at.isoformat() if self.created_at is not None else None,
        }