from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Document
from app.services.validator import validate_file, ValidationError
from app.services.storage import get_storage_service
from app.utils.helpers import (
    calculate_file_hash,
    generate_storage_key,
    sanitize_filename
)

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload a document file.
    
    Request:
        Content-Type: multipart/form-data
        Body:
            - file: File to upload (required)
            - uploaded_by: User identifier (optional)
    
    Returns:
        JSON: Document metadata and ID
        
    Status Codes:
        200: File uploaded successfully (or duplicate found)
        400: Validation error
        500: Server error
    """
    try:
        # 1. Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # 2. Get config from Flask app
        from flask import current_app
        allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
        max_file_size = current_app.config['MAX_FILE_SIZE']
        
        # 3. Validate file
        try:
            file_metadata = validate_file(file, allowed_extensions, max_file_size)
        except ValidationError as e:
            return jsonify({'error': str(e)}), 400
        
        # 4. Calculate file hash (check for duplicates)
        file_hash = calculate_file_hash(file)
        
        # Check if file already exists
        existing_doc = Document.query.filter_by(checksum=file_hash).first()
        if existing_doc:
            return jsonify({
                'message': 'File already exists',
                'duplicate': True,
                'document': existing_doc.to_dict()
            }), 200
        
        # 5. Generate storage key
        storage_key = generate_storage_key(file_metadata['filename'])
        
        # 6. Get optional parameters
        uploaded_by = request.form.get('uploaded_by', )
        
        # 7. Create database record (not committed yet)
        document = Document(
            filename=sanitize_filename(file_metadata['filename']),
            original_filename=file_metadata['filename'],
            file_size=file_metadata['file_size'],
            mime_type=file_metadata['mime_type'],
            storage_key=storage_key,
            checksum=file_hash,
            uploaded_by=uploaded_by
        )
        
        db.session.add(document)
        db.session.flush()  # Get document.id without committing
        
        # 8. Upload to MinIO
        try:
            storage_service = get_storage_service()
            storage_service.upload_file(
                file_data=file,
                storage_key=storage_key,
                content_type=file_metadata['mime_type']
            )
            
            # 9. Commit database transaction (both succeeded!)
            db.session.commit()
            
            return jsonify({
                'message': 'File uploaded successfully',
                'document': document.to_dict()
            }), 201
            
        except Exception as storage_error:
            # MinIO upload failed - rollback database
            db.session.rollback()
            raise storage_error
    
    except SQLAlchemyError as db_error:
        db.session.rollback()
        return jsonify({
            'error': 'Database error',
            'details': str(db_error)
        }), 500
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Upload failed',
            'details': str(e)
        }), 500


@upload_bp.route('/documents/<document_id>', methods=['GET'])
def get_document(document_id):
    """
    Get document metadata by ID.
    
    Args:
        document_id: Document UUID
    
    Returns:
        JSON: Document metadata
    """
    try:
        document = Document.query.get(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify(document.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@upload_bp.route('/documents/<document_id>/download', methods=['GET'])
def download_document(document_id):
    """
    Generate presigned URL for document download.
    
    Args:
        document_id: Document UUID
    
    Returns:
        JSON: Presigned download URL (expires in 24 hours)
    """
    try:
        document = Document.query.get(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        # Generate presigned URL
        storage_service = get_storage_service()
        download_url = storage_service.generate_presigned_url(
            storage_key=document.storage_key,
            expiry_hours=24
        )
        
        return jsonify({
            'document_id': str(document.id),
            'filename': document.original_filename,
            'download_url': download_url,
            'expires_in_hours': 24
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@upload_bp.route('/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """
    Delete document and its file from storage.
    
    Args:
        document_id: Document UUID
    
    Returns:
        JSON: Success message
    """
    try:
        document = Document.query.get(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        storage_key = document.storage_key
        
        # Delete from database first
        db.session.delete(document)
        db.session.commit()
        
        # Then delete from MinIO (even if this fails, DB record is gone)
        try:
            storage_service = get_storage_service()
            storage_service.delete_file(storage_key)
        except Exception as storage_error:
            # Log but don't fail the request
            print(f"Warning: Failed to delete file from storage: {storage_error}")
        
        return jsonify({
            'message': 'Document deleted successfully',
            'document_id': document_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500