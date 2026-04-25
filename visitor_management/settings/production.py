from .base import *
import os

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-key-for-dev')

# Set DEBUG to True temporarily to see errors
DEBUG = True  # Change to True for debugging

# Allow all hosts for now
ALLOWED_HOSTS = ['*']

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'vms-database'),
        'USER': os.environ.get('DB_USER', 'zjoatpflyp@vms-backend-drf'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'ocLvnMjGLP$vdi6j'),
        'HOST': os.environ.get('DB_HOST', 'vms-backend-drf.postgres.database.azure.com'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'sslmode': 'require'},
    }
}

# Disable SSL redirect to fix redirect loop
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = ['*']
CSRF_TRUSTED_ORIGINS = ['https://vms-backend-drf-avdygnb6afcchbhg.centralindia-01.azurewebsites.net']

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging - show all errors
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
