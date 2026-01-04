from minio import Minio
from minio.error import S3Error
from io import BytesIO
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """
    MinIO/S3 storage service for managing document files.
    Handles uploads, downloads, deletions, and presigned URLs.
    """
    
    def __init__(self, endpoint, access_key, secret_key, bucket_name, secure=False):
        """
        Initialize MinIO client.
        
        Args:
            endpoint: MinIO server endpoint (e.g., 'localhost:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            bucket_name: Default bucket name
            secure: Use HTTPS (True for production, False for local)
        """
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.bucket_name = bucket_name
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket already exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise
    
    def upload_file(self, file_data, storage_key, content_type=None):
        """
        Upload file to MinIO.
        
        Args:
            file_data: File-like object or bytes
            storage_key: Full path in bucket (e.g., 'documents/2025/01/file.pdf')
            content_type: MIME type (e.g., 'application/pdf')
        
        Returns:
            dict: Upload metadata (bucket, key, size)
        
        Raises:
            S3Error: If upload fails
        """
        try:
            # Convert to BytesIO if needed
            if isinstance(file_data, bytes):
                file_data = BytesIO(file_data)
            
            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Reset to beginning
            
            # Upload to MinIO
            kwargs = {
                'bucket_name': self.bucket_name,
                'object_name': storage_key,
                'data': file_data,
                'length': file_size
            }
            if content_type is not None:
                kwargs['content_type'] = content_type
            
            self.client.put_object(**kwargs)
            
            logger.info(f"Uploaded file to MinIO: {storage_key} ({file_size} bytes)")
            
            return {
                'bucket': self.bucket_name,
                'storage_key': storage_key,
                'size': file_size
            }
            
        except S3Error as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            raise
    
    def download_file(self, storage_key):
        """
        Download file from MinIO.
        
        Args:
            storage_key: Full path in bucket
        
        Returns:
            bytes: File content as bytes
        
        Raises:
            S3Error: If file not found or download fails
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=storage_key
            )
            
            # Read all data
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"Downloaded file from MinIO: {storage_key}")
            return data
            
        except S3Error as e:
            logger.error(f"Failed to download file from MinIO: {e}")
            raise
    
    def delete_file(self, storage_key):
        """
        Delete file from MinIO.
        
        Args:
            storage_key: Full path in bucket
        
        Returns:
            bool: True if deleted successfully
        
        Raises:
            S3Error: If deletion fails
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=storage_key
            )
            
            logger.info(f"Deleted file from MinIO: {storage_key}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to delete file from MinIO: {e}")
            raise
    
    def file_exists(self, storage_key):
        """
        Check if file exists in MinIO.
        
        Args:
            storage_key: Full path in bucket
        
        Returns:
            bool: True if file exists
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=storage_key
            )
            return True
        except S3Error:
            return False
    
    def get_file_metadata(self, storage_key):
        """
        Get file metadata from MinIO.
        
        Args:
            storage_key: Full path in bucket
        
        Returns:
            dict: Metadata (size, content_type, last_modified)
        
        Raises:
            S3Error: If file not found
        """
        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=storage_key
            )
            
            return {
                'size': stat.size,
                'content_type': stat.content_type,
                'last_modified': stat.last_modified,
                'etag': stat.etag
            }
            
        except S3Error as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise
    
    def generate_presigned_url(self, storage_key, expiry_hours=24):
        """
        Generate presigned URL for direct file download.
        URL expires after specified time.
        
        Args:
            storage_key: Full path in bucket
            expiry_hours: URL expiry time in hours (default: 24)
        
        Returns:
            str: Presigned URL
        
        Raises:
            S3Error: If URL generation fails
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=storage_key,
                expires=timedelta(hours=expiry_hours)
            )
            
            logger.info(f"Generated presigned URL for: {storage_key}")
            return url
            
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    
    def list_files(self, prefix='', max_keys=1000):
        """
        List files in bucket with optional prefix filter.
        
        Args:
            prefix: Filter by prefix (e.g., 'documents/2025/01/')
            max_keys: Maximum number of files to return
        
        Returns:
            list: List of file objects
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            files = []
            for obj in objects:
                if len(files) >= max_keys:
                    break
                    
                files.append({
                    'storage_key': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified
                })
            
            return files
            
        except S3Error as e:
            logger.error(f"Failed to list files: {e}")
            raise


# Singleton instance (initialized in Flask app)
storage_service = None


def init_storage_service(app):
    """
    Initialize storage service from Flask config.
    Call this in create_app().
    
    Args:
        app: Flask application instance
    """
    global storage_service
    
    storage_service = StorageService(
        endpoint=app.config['MINIO_ENDPOINT'],
        access_key=app.config['MINIO_ACCESS_KEY'],
        secret_key=app.config['MINIO_SECRET_KEY'],
        bucket_name=app.config['MINIO_BUCKET'],
        secure=app.config['MINIO_SECURE']
    )
    
    logger.info("Storage service initialized")
    return storage_service


def get_storage_service():
    """
    Get storage service instance.
    Use this in routes/tasks.
    
    Returns:
        StorageService: Initialized storage service
    
    Raises:
        RuntimeError: If service not initialized
    """
    if storage_service is None:
        raise RuntimeError("Storage service not initialized. Call init_storage_service() first.")
    
    return storage_service