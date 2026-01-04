import hashlib
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename


def sanitize_filename(filename):
    """
    Remove dangerous characters from filename.
    
    Examples:
        '../../../etc/passwd' -> 'etc_passwd'
        'My Invoice (2024)!.pdf' -> 'My_Invoice_2024.pdf'
    """
    # Use werkzeug's secure_filename (removes path separators, special chars)
    safe_name = secure_filename(filename)
    
    # Additional cleaning: replace spaces and parentheses
    safe_name = re.sub(r'[^\w\s.-]', '', safe_name)  # Keep alphanumeric, spaces, dots, hyphens
    safe_name = safe_name.replace(' ', '_')  # Spaces to underscores
    
    return safe_name


def generate_storage_key(filename, prefix='documents'):
    """
    Generate unique storage key for MinIO.
    
    Pattern: documents/2025/01/04/abc123_filename.pdf
    
    Args:
        filename: Original filename
        prefix: Folder prefix (default: 'documents')
    
    Returns:
        str: Full MinIO storage key
    """
    # Get current date for folder structure
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    
    # Generate unique ID (first 8 chars of UUID)
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    # Sanitize filename
    safe_filename = sanitize_filename(filename)
    
    # Build storage key: documents/2025/01/04/abc123_invoice.pdf
    storage_key = f"{prefix}/{year}/{month}/{day}/{unique_id}_{safe_filename}"
    
    return storage_key


def generate_output_storage_key(job_id, result_type, extension):
    """
    Generate storage key for job output files.
    
    Pattern: results/job_abc123/extracted_tables.csv
    
    Args:
        job_id: Job UUID
        result_type: Type of result (e.g., 'output_csv', 'extracted_tables')
        extension: File extension (e.g., 'csv', 'xlsx', 'pdf')
    
    Returns:
        str: Storage key for output file
    """
    # Use first 8 chars of job_id for readability
    short_job_id = str(job_id)[:8]
    
    # Build key: results/job_abc123/output_csv.csv
    storage_key = f"results/job_{short_job_id}/{result_type}.{extension}"
    
    return storage_key


def calculate_file_hash(file_stream):
    """
    Calculate SHA256 hash of file content.
    Used to detect duplicate uploads.
    
    Args:
        file_stream: File-like object (from request.files)
    
    Returns:
        str: Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()
    
    # Read file in chunks to handle large files
    for byte_block in iter(lambda: file_stream.read(4096), b""):
        sha256_hash.update(byte_block)
    
    # Reset file pointer to beginning (important!)
    file_stream.seek(0)
    
    return sha256_hash.hexdigest()


def get_file_extension(filename):
    """
    Extract file extension from filename.
    
    Examples:
        'document.pdf' -> 'pdf'
        'data.tar.gz' -> 'gz'
    
    Returns:
        str: Lowercase extension without dot
    """
    return os.path.splitext(filename)[1][1:].lower()


def format_file_size(size_bytes):
    """
    Convert bytes to human-readable format.
    
    Examples:
        1024 -> '1.0 KB'
        1048576 -> '1.0 MB'
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        str: Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"