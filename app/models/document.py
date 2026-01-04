from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app import db  # We'll create this in app/__init__.py


class Document(db.Model):
    """
    Represents an uploaded document file.
    
    Stores metadata about the file, while actual file bytes live in MinIO.
    
    """
    __tablename__ = 'documents'
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # File Information
    filename = Column(String(255), nullable=False)  # Generated safe name
    original_filename = Column(String(255), nullable=False)  # User's original name
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=False)  # e.g., 'application/pdf'
    
    # Storage
    storage_key = Column(String(500), nullable=False, unique=True)  # Path in MinIO
    checksum = Column(String(64), nullable=False)  # SHA256 hash for integrity
    
    # Metadata
    uploaded_by = Column(String(100))  # User identifier (for future multi-tenancy)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
  
    metadata_ = Column('metadata', JSONB)  # Flexible JSON: {page_count: 5, language: 'en'}
    
    # Relationships
    # One document can have many processing jobs
    jobs = relationship('ProcessingJob', back_populates='document', cascade='all, delete-orphan')
    
    # Indexes (defined at class level)
    __table_args__ = (
        Index('idx_documents_uploaded_by', 'uploaded_by'),
        Index('idx_documents_uploaded_at', 'uploaded_at'),
        Index('idx_documents_checksum', 'checksum'),
    )
    
    def __repr__(self):
        return f'<Document {self.filename} ({self.file_size} bytes)>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON responses."""
        return {
            'id': str(self.id),
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'storage_key': self.storage_key,
            'uploaded_by': self.uploaded_by,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at is not None else None,
            'metadata': self.metadata_,
        }