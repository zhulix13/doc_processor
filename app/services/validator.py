import magic
from werkzeug.datastructures import FileStorage
from app.utils.helpers import get_file_extension


class ValidationError(Exception):
    """Custom exception for file validation errors"""
    pass


def validate_file(file: FileStorage, allowed_extensions: set, max_size: int):
    """
    Validate uploaded file for security and compliance.
    
    Checks (in order of speed):
    1. File exists
    2. File size
    3. File extension
    4. MIME type (content analysis)
    
    Args:
        file: Werkzeug FileStorage object from request.files
        allowed_extensions: Set of allowed extensions (e.g., {'pdf', 'csv'})
        max_size: Maximum file size in bytes
    
    Raises:
        ValidationError: If validation fails
    
    Returns:
        dict: File metadata (filename, size, mime_type, extension)
    """
    
    # Check 1: File exists and has filename
    if not file or not file.filename:
        raise ValidationError("No file provided")
    
    filename = file.filename
    
    # Check 2: File size (seek to end to get size)
    file.seek(0, 2)  # Seek to end of file
    file_size = file.tell()  # Get position (= file size)
    file.seek(0)  # Reset to beginning
    
    if file_size == 0:
        raise ValidationError("File is empty")
    
    if file_size > max_size:
        from app.utils.helpers import format_file_size
        raise ValidationError(
            f"File too large. Maximum size: {format_file_size(max_size)}, "
            f"uploaded: {format_file_size(file_size)}"
        )
    
    # Check 3: File extension
    extension = get_file_extension(filename)
    
    if not extension:
        raise ValidationError("File has no extension")
    
    if extension not in allowed_extensions:
        raise ValidationError(
            f"File type '.{extension}' not allowed. "
            f"Allowed types: {', '.join(sorted(allowed_extensions))}"
        )
    
    # Check 4: MIME type (content analysis using python-magic)
    file_content = file.read(2048)  # Read first 2KB for magic bytes
    file.seek(0)  # Reset pointer
    
    mime_type = magic.from_buffer(file_content, mime=True)
    
    # Validate MIME type matches extension
    if not _is_mime_type_valid(mime_type, extension):
        raise ValidationError(
            f"File content type '{mime_type}' does not match extension '.{extension}'. "
            f"Possible file spoofing detected."
        )
    
    # Return validated file metadata
    return {
        'filename': filename,
        'file_size': file_size,
        'mime_type': mime_type,
        'extension': extension,
    }


def _is_mime_type_valid(mime_type: str, extension: str) -> bool:
    """
    Check if MIME type matches file extension.
    
    Args:
        mime_type: Detected MIME type (e.g., 'application/pdf')
        extension: File extension (e.g., 'pdf')
    
    Returns:
        bool: True if MIME type matches extension
    """
    
    # Mapping of extensions to accepted MIME types
    MIME_TYPE_MAP = {
        'pdf': ['application/pdf'],
        'docx': [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/zip',  # DOCX is actually a ZIP file
        ],
        'xlsx': [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/zip',
        ],
        'csv': ['text/csv', 'text/plain', 'application/csv'],
        'jpg': ['image/jpeg'],
        'jpeg': ['image/jpeg'],
        'png': ['image/png'],
    }
    
    allowed_mime_types = MIME_TYPE_MAP.get(extension, [])
    
    if not allowed_mime_types:
        # Extension not in map - be permissive
        return True
    
    return mime_type in allowed_mime_types


def validate_job_type(job_type: str, valid_job_types: list) -> None:
    """
    Validate job type is supported.
    
    Args:
        job_type: Requested job type
        valid_job_types: List of valid job types from config
    
    Raises:
        ValidationError: If job type is invalid
    """
    if job_type not in valid_job_types:
        raise ValidationError(
            f"Invalid job type '{job_type}'. "
            f"Supported types: {', '.join(valid_job_types)}"
        )


def validate_job_options(job_type: str, options: dict) -> dict:
    """
    Validate job-specific options.
    
    Args:
        job_type: Type of job
        options: Job options dictionary
    
    Returns:
        dict: Validated and sanitized options
    
    Raises:
        ValidationError: If options are invalid
    """
    if options is None:
        return {}
    
    # Job-specific validation rules
    if job_type == 'ocr_document':
        # OCR requires language specification
        if 'language' not in options:
            options['language'] = 'eng'  # Default to English
        
        valid_languages = ['eng', 'fra', 'spa', 'deu']  # Extend as needed
        if options['language'] not in valid_languages:
            raise ValidationError(
                f"Invalid OCR language. Supported: {', '.join(valid_languages)}"
            )
    
    elif job_type == 'convert_to_excel':
        # Validate sheet name if provided
        if 'sheet_name' in options:
            sheet_name = options['sheet_name']
            if len(sheet_name) > 31:  # Excel limit
                raise ValidationError("Sheet name cannot exceed 31 characters")
    
    return options