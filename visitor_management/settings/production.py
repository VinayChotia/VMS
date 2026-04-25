from .base import *
import os

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-key-for-dev')
DEBUG = False
ALLOWED_HOSTS = ['*']

# PostgreSQL database configuration with new password
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'vms-database',
        'USER': 'zjoatpflyp',
        'PASSWORD': 'Hello$321',  # Updated password
        'HOST': 'vms-backend-drf.postgres.database.azure.com',
        'PORT': '5432',
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CORS_ALLOW_ALL_ORIGINS = True

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
