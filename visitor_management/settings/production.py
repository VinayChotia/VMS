from .base import *
import os

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-key-for-dev')
DEBUG = False
ALLOWED_HOSTS = ['*']

# PostgreSQL database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'vms-database'),
        'USER': os.environ.get('DB_USER', 'zjoatpflyp@vms-backend-drf'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'ocLvnMjGLP$vdi6j'),
        'HOST': os.environ.get('DB_HOST', 'vms-backend-drf.postgres.database.azure.com'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Security settings
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# CORS settings - Fixed format
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    'https://vms-backend-drf-avdygnb6afcchbhg.centralindia-01.azurewebsites.net'
]
CSRF_TRUSTED_ORIGINS = [
    'https://vms-backend-drf-avdygnb6afcchbhg.centralindia-01.azurewebsites.net'
]

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
