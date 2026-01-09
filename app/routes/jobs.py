from flask import Blueprint, request, jsonify

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Document, ProcessingJob, JobResult
from app.services.validator import validate_job_type, validate_job_options, ValidationError

import logging

logger = logging.getLogger(__name__)
jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/jobs', methods=['POST'])
def create_job():
    """
    Create a new processing job.
    
    Request Body:
        {
            "document_id": "uuid",
            "job_type": "extract_data",
            "options": {"ocr_language": "eng"}  // Optional
        }
    
    Returns:
        JSON: Created job details
    """
    try:
        data = request.get_json()
        
        # 1. Validate request body
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        document_id = data.get('document_id')
        job_type = data.get('job_type')
        options = data.get('options', {})
        
        if not document_id:
            return jsonify({'error': 'document_id is required'}), 400
        
        if not job_type:
            return jsonify({'error': 'job_type is required'}), 400
        
        # 2. Check if document exists
        document = Document.query.get(document_id)
        if not document:
            return jsonify({'error': f'Document {document_id} not found'}), 404
        
        # 3. Validate job type
        from flask import current_app
        valid_job_types = current_app.config['VALID_JOB_TYPES']
        
        try:
            validate_job_type(job_type, valid_job_types)
            validated_options = validate_job_options(job_type, options)
        except ValidationError as e:
            return jsonify({'error': str(e)}), 400
        
        # 4. Create job in database
        job = ProcessingJob(
            document_id=document_id,
            job_type=job_type,
            options_=validated_options,
            status='queued'
        )
        
        db.session.add(job)
        db.session.commit()
        
       
        try:
            if job_type == 'extract_data':
                from app.tasks.processing_tasks import extract_data_task
                celery_task = extract_data_task.delay(str(job.id))
                
                # Save Celery task ID
                job.celery_task_id = celery_task.id
                db.session.commit()
                
                logger.info(f"Queued Celery task {celery_task.id} for job {job.id}")
            else:
                # Other job types not implemented yet
                logger.warning(f"Job type '{job_type}' queued but no task handler available yet")
        
        except Exception as celery_error:
            logger.error(f"Failed to queue Celery task: {celery_error}")
            # Don't fail the request - job is still created, can retry manually
        
        return jsonify({
            'message': 'Job created and queued successfully',
            'job': job.to_dict()
        }), 201
        
        
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create job', 'details': str(e)}), 500


@jobs_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """
    Get job status and details.
    
    Args:
        job_id: Job UUID
    
    Returns:
        JSON: Job details including status, progress, errors
    """
    try:
        job = ProcessingJob.query.get(job_id)
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Include document info and result count
        job_data = job.to_dict()
        job_data['document'] = job.document.to_dict()
        job_data['result_count'] = len(job.results)
        job_data['has_results'] = len(job.results) > 0
        
        return jsonify(job_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jobs_bp.route('/jobs/<job_id>/results', methods=['GET'])
def get_job_results(job_id):
    """
    Get all results for a job (metadata only).
    
    Args:
        job_id: Job UUID
    
    Returns:
        JSON: List of result metadata
    """
    try:
        job = ProcessingJob.query.get(job_id)
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        if job.status != 'completed':
            return jsonify({
                'error': 'Job not completed yet',
                'status': job.status
            }), 400
        
        # Return metadata for each result
        results_metadata = []
        for result in job.results:
            metadata = {
                'id': str(result.id),
                'result_type': result.result_type,
                'has_data': result.result_data is not None,
                'has_file': result.output_file_key is not None,
                'file_size': result.file_size,
                'mime_type': result.mime_type,
                'created_at': result.created_at.isoformat()
            }
            results_metadata.append(metadata)
        
        return jsonify({
            'job_id': job_id,
            'result_count': len(results_metadata),
            'results': results_metadata
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jobs_bp.route('/jobs/<job_id>/results/<result_type>', methods=['GET'])
def get_job_result_by_type(job_id, result_type):
    """
    Get specific result by type.
    
    Args:
        job_id: Job UUID
        result_type: Result type (e.g., 'extracted_text', 'output_csv')
    
    Returns:
        JSON: Result data or download URL for files
    """
    try:
        job = ProcessingJob.query.get(job_id)
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Find result by type
        result = JobResult.query.filter_by(
            job_id=job_id,
            result_type=result_type
        ).first()
        
        if not result:
            return jsonify({
                'error': f'Result type "{result_type}" not found for this job'
            }), 404
        
        # If result has file, generate download URL
        if result.output_file_key:
            from app.services.storage import get_storage_service
            storage_service = get_storage_service()
            
            download_url = storage_service.generate_presigned_url(
                storage_key=result.output_file_key,
                expiry_hours=24
            )
            
            return jsonify({
                'result_type': result.result_type,
                'file_size': result.file_size,
                'mime_type': result.mime_type,
                'download_url': download_url,
                'expires_in_hours': 24
            }), 200
        
        # If result has JSON data, return it directly
        if result.result_data:
            return jsonify({
                'result_type': result.result_type,
                'data': result.result_data
            }), 200
        
        return jsonify({'error': 'Result has no data'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jobs_bp.route('/documents/<document_id>/jobs', methods=['GET'])
def get_document_jobs(document_id):
    """
    Get all jobs for a specific document.
    
    Args:
        document_id: Document UUID
    
    Returns:
        JSON: List of jobs for the document
    """
    try:
        document = Document.query.get(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        jobs = ProcessingJob.query.filter_by(document_id=document_id)\
            .order_by(ProcessingJob.created_at.desc())\
            .all()
        
        jobs_list = [job.to_dict() for job in jobs]
        
        return jsonify({
            'document_id': document_id,
            'job_count': len(jobs_list),
            'jobs': jobs_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jobs_bp.route('/jobs/<job_id>', methods=['DELETE'])
def cancel_job(job_id):
    """
    Cancel a running job.
    
    Args:
        job_id: Job UUID
    
    Returns:
        JSON: Cancellation status
    """
    try:
        job = ProcessingJob.query.get(job_id)
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        if job.status == 'completed':
            return jsonify({'error': 'Cannot cancel completed job'}), 400
        
        if job.status == 'failed':
            return jsonify({'error': 'Cannot cancel failed job'}), 400
        
        # TODO: Cancel Celery task (Phase 3)
        # if job.celery_task_id:
        #     from app import celery
        #     celery.control.revoke(job.celery_task_id, terminate=True)
        
        # Update job status
        job.status = 'cancelled'
        db.session.commit()
        
        return jsonify({
            'message': 'Job cancelled successfully',
            'job_id': job_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@jobs_bp.route('/jobs/<job_id>/retry', methods=['POST'])
def retry_job(job_id):
    """
    Retry a failed job.
    Creates a new job with same parameters.
    
    Args:
        job_id: Job UUID of failed job
    
    Returns:
        JSON: New job details
    """
    try:
        old_job = ProcessingJob.query.get(job_id)
        
        if not old_job:
            return jsonify({'error': 'Job not found'}), 404
        
        if old_job.status != 'failed':
            return jsonify({
                'error': f'Can only retry failed jobs. Current status: {old_job.status}'
            }), 400
        
        # Create new job with same parameters
        new_job = ProcessingJob(
            document_id=old_job.document_id,
            job_type=old_job.job_type,
            options_=old_job.options_,
            status='queued'
        )
        
        db.session.add(new_job)
        db.session.commit()
        
        # TODO: Send to Celery (Phase 3)
        
        return jsonify({
            'message': 'Job retry created',
            'original_job_id': job_id,
            'new_job': new_job.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500