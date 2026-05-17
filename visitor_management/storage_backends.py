# visitor_management/storage_backends.py
"""
Custom storage backends for Azure Blob Storage.
"""

from storages.backends.azure_storage import AzureStorage
import os
import logging

logger = logging.getLogger(__name__)

class AzureMediaStorage(AzureStorage):
    """
    Azure Storage backend for media files.
    Uses environment variables for configuration.
    """
    account_name = os.environ.get('AZURE_ACCOUNT_NAME')
    account_key = os.environ.get('AZURE_ACCOUNT_KEY')
    azure_container = os.environ.get('AZURE_MEDIA_CONTAINER', 'media')
    expiration_secs = None  # No expiration for media files
    azure_ssl = True
    overwrite_files = False  # Don't overwrite existing files
    file_overwrite = False   # Alias for older versions
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Validate configuration
        if not self.account_name:
            logger.warning("AZURE_ACCOUNT_NAME is not set in environment variables")
        if not self.account_key:
            logger.warning("AZURE_ACCOUNT_KEY is not set in environment variables")
        if not self.azure_container:
            logger.warning("AZURE_MEDIA_CONTAINER is not set, using default 'media'")
        
        # Log successful initialization
        if self.account_name and self.account_key:
            logger.info(f"AzureMediaStorage initialized with account: {self.account_name}, container: {self.azure_container}")
    
    def url(self, name, expire=None):
        """
        Generate URL for the given blob name.
        """
        if expire is None:
            expire = self.expiration_secs
        url = super().url(name, expire)
        logger.debug(f"Generated URL for {name}: {url}")
        return url