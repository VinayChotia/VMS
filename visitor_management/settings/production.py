# """
# Production settings for visitor_management project.
# These settings are for production environment.
# """

# from .base import *
# import os
# # Remove django_heroku import

# # SECURITY WARNING: keep the secret key used in production secret!
# # Should be set via environment variable
# SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-production-secret-key-here')

# # SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = False

# # Production allowed hosts - MUST be configured properly
# ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
# # Example: ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com', 'your-server-ip']

# # Database - Production database (use environment variables)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('DB_NAME', 'visitor_db_prod'),
#         'USER': os.environ.get('DB_USER', ''),
#         'PASSWORD': os.environ.get('DB_PASSWORD', ''),
#         'HOST': os.environ.get('DB_HOST', 'localhost'),
#         'PORT': os.environ.get('DB_PORT', '5432'),
#         'CONN_MAX_AGE': 60,  # Connection persistence
#         'OPTIONS': {
#             'sslmode': 'require',  # Enable SSL for production database
#         },
#     }
# }

# # CORS Settings - Production (restrict origins)
# CORS_ALLOW_ALL_ORIGINS = True
# CORS_ALLOW_CREDENTIALS = True
# CORS_ALLOW_HEADERS = ['*']
# CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
# # Example: CORS_ALLOWED_ORIGINS = ['https://yourdomain.com', 'https://www.yourdomain.com']

# CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
# # Example: CSRF_TRUSTED_ORIGINS = ['https://yourdomain.com']

# # Security Settings for Production
# SECURE_SSL_REDIRECT = False
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# X_FRAME_OPTIONS = 'DENY'
# SECURE_HSTS_SECONDS = 31536000  # 1 year
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# # JWT Settings - Production (more secure)
# SIMPLE_JWT = {
#     **SIMPLE_JWT,  # Inherit from base
#     'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # Shorter lifetime for production
#     'REFRESH_TOKEN_LIFETIME': timedelta(hours=12),
#     'AUTH_HEADER_TYPES': ('Bearer',),
# }

# # Email backend for production
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
# EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# # Cache backend for production (using Redis or Memcached)
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     } if os.environ.get('REDIS_URL') else {
#         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#     }
# }

# # CHANNEL_LAYERS - No Redis required
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels.layers.InMemoryChannelLayer"
#     },
# }

# # Azure Storage Settings
# AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME')
# AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY')
# AZURE_MEDIA_CONTAINER = os.environ.get('AZURE_MEDIA_CONTAINER', 'media')

# # Static and Media files in production
# STORAGES = {
#     "default": {
#         "BACKEND": "visitor_management.storage_backends.AzureMediaStorage",
#     },
#     "staticfiles": {
#         "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
#     },
# }

# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# # Media files in production
# MEDIA_URL = f'https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_MEDIA_CONTAINER}/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# # Force Django to serve media files even in production (for testing only)
# # WARNING: Only use this for testing, not for production!
# import warnings
# warnings.warn("Media files are being served by Django. This is inefficient for production!")

# # Disable security for media serving (for testing only)
# SECURE_SSL_REDIRECT = False  # Temporarily disable for testing

# # Make sure the media directory exists
# os.makedirs(MEDIA_ROOT, exist_ok=True)

# # Logging for production
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'verbose': {
#             'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
#             'style': '{',
#         },
#     },
#     'handlers': {
#         'file': {
#             'level': 'ERROR',
#             'class': 'logging.FileHandler',
#             'filename': os.path.join(BASE_DIR, 'logs/django.errors.log'),
#             'formatter': 'verbose',
#         },
#         'console': {
#             'level': 'INFO',
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'root': {
#         'handlers': ['console', 'file'],
#         'level': 'INFO',
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['file'],
#             'level': 'ERROR',
#             'propagate': False,
#         },
#     },
# }

# # Ensure logs directory exists
# os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)


"""
Production settings for visitor_management project.
These settings are for production environment.
"""

from .base import *
import os
from datetime import timedelta

# SECURITY WARNING: keep the secret key used in production secret!
# Should be set via environment variable
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-production-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Production allowed hosts - MUST be configured properly
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
# Example: ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com', 'your-server-ip']

# Database - Production database (use environment variables)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'visitor_db_prod'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,  # Connection persistence
        'OPTIONS': {
            'sslmode': 'require',  # Enable SSL for production database
        },
    }
}

# CORS Settings - Production (restrict origins)
CORS_ALLOW_ALL_ORIGINS = False  # Changed to False for production
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ['*']
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
# Example: CORS_ALLOWED_ORIGINS = ['https://yourdomain.com', 'https://www.yourdomain.com']

# Add your frontend URL to allowed origins
if os.environ.get('FRONTEND_URL'):
    CORS_ALLOWED_ORIGINS.append(os.environ.get('FRONTEND_URL'))

CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
# Example: CSRF_TRUSTED_ORIGINS = ['https://yourdomain.com']

# Security Settings for Production
SECURE_SSL_REDIRECT = True  # Changed to True for production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# JWT Settings - Production (more secure)
SIMPLE_JWT = {
    **SIMPLE_JWT,  # Inherit from base
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # Shorter lifetime for production
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=12),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Email backend for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Cache backend for production (using Redis or Memcached)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    } if os.environ.get('REDIS_URL') else {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# CHANNEL_LAYERS - No Redis required
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    },
}

# ========== AZURE STORAGE CONFIGURATION ==========
# Azure Storage Settings
AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME','vmsmediastore2026')
AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY')
AZURE_MEDIA_CONTAINER = os.environ.get('AZURE_MEDIA_CONTAINER', 'media')
AZURE_URL_EXPIRATION_SECS = None  # No expiration for media files
AZURE_STATIC_CONTAINER='static'  # Optional - if you want to store static files
AZURE_BACKUP_CONTAINER='media-backup'
AZURE_TEMP_CONTAINER='temp'
AZURE_STORAGE_URL='https://vmsmediastore2026.blob.core.windows.net'
AZURE_MEDIA_URL='https://vmsmediastore2026.blob.core.windows.net/media'
AZURE_STATIC_URL='https://vmsmediastore2026.blob.core.windows.net/static'

# Validate Azure Storage configuration (optional but recommended)
if not AZURE_ACCOUNT_NAME or not AZURE_ACCOUNT_KEY:
    import warnings
    warnings.warn(
        "Azure Storage credentials are not configured. "
        "Media files will not be stored in Azure!",
        RuntimeWarning
    )

# Static and Media files in production
STORAGES = {
    "default": {
        "BACKEND": "visitor_management.storage_backends.AzureMediaStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Media files configuration for Azure
if AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY:
    # Use Azure Storage for media files
    MEDIA_URL = f'https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_MEDIA_CONTAINER}/'
    # MEDIA_ROOT is not used with Azure Storage, but define it for compatibility
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    
    # Ensure the media directory exists locally (for any local fallbacks)
    os.makedirs(MEDIA_ROOT, exist_ok=True)
else:
    # Fallback to local storage if Azure credentials are missing
    import warnings
    warnings.warn(
        "Azure Storage credentials missing. Falling back to local file storage. "
        "This is not recommended for production!",
        RuntimeWarning
    )
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    os.makedirs(MEDIA_ROOT, exist_ok=True)

# Logging for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/django.errors.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # Add Azure Storage specific logging
        'azure_storage': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/azure_storage.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'storages': {
            'handlers': ['azure_storage'],
            'level': 'WARNING',
            'propagate': False,
        },
        'azure.storage': {
            'handlers': ['azure_storage'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Ensure logs directory exists
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Additional Production Settings
# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours in seconds
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# File upload settings
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
DATA_UPLOAD_MAX_NUMBER_FILES = 100
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25 MB

# Maximum size for file uploads (10 MB)
MAX_UPLOAD_SIZE = 10485760

# Security headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Frontend URL for QR codes and redirects
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://vmsfrontend2026.z29.web.core.windows.net')