from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from botocore.exceptions import ClientError
import logging


logger = logging.getLogger(__name__)

class MediaStorage(S3Boto3Storage):
    """
    Custom S3 storage backend with correct URL handling
    """
    location = 'media'
    default_acl = 'public-read'  # Changed to public-read so URLs work
    file_overwrite = True
    custom_domain = False
    querystring_auth = False  # Disable signed URLs for public files

    def __init__(self, *args, **kwargs):
        kwargs['bucket_name'] = settings.AWS_STORAGE_BUCKET_NAME
        kwargs['region_name'] = settings.AWS_S3_REGION_NAME
        kwargs['endpoint_url'] = settings.AWS_S3_ENDPOINT_URL
        super().__init__(*args, **kwargs)
    
    def exists(self, name):
        """Handle permission errors gracefully"""
        try:
            return super().exists(name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['403', 'Forbidden', 'AccessDenied']:
                logger.warning(f"Permission denied checking if {name} exists. Proceeding with upload.")
                return False
            else:
                raise e

    def get_available_name(self, name, max_length=None):
        """Handle cases where we can't check file existence"""
        try:
            return super().get_available_name(name, max_length)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['403', 'Forbidden', 'AccessDenied']:
                logger.warning(f"Permission denied checking availability of {name}. Using original name.")
                return name
            else:
                raise e

    def _save(self, name, content):
        """Save with better error handling"""
        try:
            return super()._save(name, content)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            logger.error(f"S3 Upload Error for {name}: {error_code} - {str(e)}")
            
            if error_code in ['403', 'Forbidden', 'AccessDenied']:
                raise Exception(f"Permission denied uploading to S3.")
            else:
                raise e

    def url(self, name):
        """
        Generate the correct URL for S3 objects
        """
        try:
            # For public files, return direct S3 URL
            if self.custom_domain:
                return f"https://{self.custom_domain}/{self.location}/{name}"
            else:
                # Use the standard S3 URL format
                return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{self.location}/{name}"
        except Exception as e:
            logger.error(f"Error generating URL for {name}: {e}")
            # Fallback URL
            return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{self.location}/{name}"

class StaticStorage(S3Boto3Storage):
    """
    Static files storage backend
    """
    location = 'static'
    default_acl = 'public-read'
    file_overwrite = True
    custom_domain = False

    def __init__(self, *args, **kwargs):
        kwargs['bucket_name'] = settings.AWS_STORAGE_BUCKET_NAME
        kwargs['region_name'] = settings.AWS_S3_REGION_NAME
        kwargs['endpoint_url'] = settings.AWS_S3_ENDPOINT_URL
        super().__init__(*args, **kwargs)