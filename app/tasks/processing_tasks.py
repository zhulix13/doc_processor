"""
Main document processing tasks.
Orchestrates extraction services and manages job lifecycle.
"""

import logging
from datetime import datetime
from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError
from io import BytesIO

from app import db
from app.models import ProcessingJob, JobResult
from app.services.storage import get_storage_service
from app.services.extractors import extract_from_pdf, extract_from_csv, extract_from_excel

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def extract_data_task(self, job_id):
    """
    Extract all data from a document (text, tables, metadata).
    Routes to appropriate extractor based on file type.
    
    Args:
        job_id: UUID of the processing job
    
    Returns:
        dict: Summary of extraction results
    """
    job = None
    
    try:
        # 1. Get job and update status to processing
        job = ProcessingJob.query.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        logger.info(f"Starting extract_data task for job {job_id}")
        
        job.status = 'processing'
        job.started_at = datetime.utcnow()
        job.celery_task_id = self.request.id
        db.session.commit()
        
        # 2. Download file from MinIO
        storage_service = get_storage_service()
        document = job.document
        
        logger.info(f"Downloading file: {document.storage_key}")
        file_data = storage_service.download_file(document.storage_key)
        
        # 3. Route to appropriate extractor based on MIME type
        mime_type = document.mime_type
        
        logger.info(f"Processing file type: {mime_type}")
        
        if mime_type == 'application/pdf':
            results = extract_from_pdf(file_data)
        elif mime_type in ['text/csv', 'text/plain']:
            results = extract_from_csv(file_data)
        elif mime_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
            results = extract_from_excel(file_data)
        else:
            raise ValueError(f"Unsupported file type: {mime_type}")
        
        # 4. Save each result to database (separate transactions for idempotency)
        for result_type, result_data in results.items():
            _save_result(job_id, result_type, result_data)
        
        # 5. Mark job as completed
        job = ProcessingJob.query.get(job_id)  # Refetch to avoid stale data
        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Job {job_id} completed successfully with {len(results)} results")
        
        return {
            'job_id': str(job_id),
            'status': 'completed',
            'results_count': len(results),
            'result_types': list(results.keys())
        }
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
        
        # Update job status to failed
        try:
            db.session.rollback()
            job = ProcessingJob.query.get(job_id)  # Refetch
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                job.error_trace = str(self.request.traceback) if hasattr(self.request, 'traceback') else None
                job.retry_count += 1
                db.session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")
        
        # Retry with exponential backoff if retries remaining
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries * 60  # 1min, 2min, 4min
            logger.info(f"Retrying job {job_id} in {countdown} seconds (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=countdown)
        else:
            logger.error(f"Job {job_id} failed permanently after {self.max_retries} retries")
            raise


def _save_result(job_id, result_type, result_data):
    """
    Save a single result to database.
    Idempotent - checks if result already exists before saving.
    
    Args:
        job_id: Job UUID
        result_type: Type of result (e.g., 'extracted_text')
        result_data: Result data as dictionary
    """
    try:
        # Check if result already exists (idempotency)
        existing = JobResult.query.filter_by(
            job_id=job_id,
            result_type=result_type
        ).first()
        
        if existing:
            logger.info(f"Result '{result_type}' already exists for job {job_id}, skipping")
            return
        
        # Create new result
        result = JobResult(
            job_id=job_id,
            result_type=result_type,
            result_data=result_data
        )
        
        db.session.add(result)
        db.session.commit()
        
        logger.info(f"Saved result '{result_type}' for job {job_id}")
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Failed to save result '{result_type}': {e}")
        raise