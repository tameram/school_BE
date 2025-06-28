import boto3
from django.conf import settings
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)


class S3FileManager:
    def __init__(self, skip_connection_test=True):
        """
        Initialize S3 client with optional connection testing
        
        Args:
            skip_connection_test (bool): Skip the initial connection test to avoid permission errors
        """
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
                endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
            )
            self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            
            # Only test connection if explicitly requested
            if not skip_connection_test:
                self._test_connection()
            else:
                logger.info("S3FileManager initialized (connection test skipped)")
                
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            # Don't raise exception, allow system to continue
            self.s3_client = None
            self.bucket_name = None
        except Exception as e:
            logger.warning(f"S3 initialization warning: {e}")
            # Don't raise exception, allow system to continue
            self.s3_client = None
            self.bucket_name = None

    def _test_connection(self):
        """Test S3 connection and permissions"""
        try:
            # Try to list bucket contents (should work with basic permissions)
            self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            logger.info("S3 connection test successful")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['403', 'Forbidden', 'AccessDenied']:
                logger.warning("S3 connection established but permissions are limited")
                # Don't raise exception for permission issues
            else:
                logger.error(f"S3 connection test failed: {e}")
                raise e

    def generate_presigned_url(self, object_key, expiration=3600):
        """Generate a presigned URL for S3 object"""
        if not self.s3_client or not self.bucket_name:
            logger.warning("S3 client not available for presigned URL generation")
            return None
            
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Error generating presigned URL for {object_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL for {object_key}: {e}")
            return None

    def delete_file(self, object_key):
        """Delete file from S3"""
        if not self.s3_client or not self.bucket_name:
            logger.warning("S3 client not available for file deletion")
            return False
            
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logger.info(f"Successfully deleted {object_key}")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                logger.info(f"File {object_key} doesn't exist, considering it deleted")
                return True
            else:
                logger.error(f"Error deleting file {object_key}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error deleting file {object_key}: {e}")
            return False

    def file_exists(self, object_key):
        """Check if file exists in S3"""
        if not self.s3_client or not self.bucket_name:
            logger.warning("S3 client not available for existence check")
            return False
            
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['404', 'NoSuchKey']:
                return False
            elif error_code in ['403', 'Forbidden', 'AccessDenied']:
                logger.warning(f"Permission denied checking existence of {object_key}")
                return False  # Assume doesn't exist if we can't check
            else:
                logger.error(f"Error checking file existence {object_key}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking file existence {object_key}: {e}")
            return False

    def list_files(self, prefix):
        """List files with given prefix"""
        if not self.s3_client or not self.bucket_name:
            logger.warning("S3 client not available for file listing")
            return []
            
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, 
                Prefix=prefix
            )
            return response.get('Contents', [])
        except ClientError as e:
            logger.error(f"Error listing files with prefix {prefix}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing files with prefix {prefix}: {e}")
            return []

    def get_file_info(self, object_key):
        """Get file metadata"""
        if not self.s3_client or not self.bucket_name:
            logger.warning("S3 client not available for file info")
            return None
            
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            return {
                'size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType'),
            }
        except ClientError as e:
            logger.error(f"Error getting file info for {object_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting file info for {object_key}: {e}")
            return None

    def is_available(self):
        """Check if S3 client is available and working"""
        return self.s3_client is not None and self.bucket_name is not None
