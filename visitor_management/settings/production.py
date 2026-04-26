from .base import *
import os

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-key-for-dev')
DEBUG = False
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'vms-database',
        'USER': 'zjoatpflyp',
        'PASSWORD': 'Hello$321',
        'HOST': 'vms-backend-drf.postgres.database.azure.com',
        'PORT': '5432',
        'CONN_MAX_AGE': 0,
        'OPTIONS': {'sslmode': 'require'},
    }
}

# Security settings for HTTPS
SECURE_SSL_REDIRECT = False  # Azure handles SSL
SESSION_COOKIE_SECURE = True  # Send cookie only over HTTPS
CSRF_COOKIE_SECURE = True     # Send CSRF cookie only over HTTPS
CSRF_USE_SESSIONS = False      # Store CSRF token in cookie (not session)
CSRF_COOKIE_HTTPONLY = False   # Allow JavaScript to read CSRF token

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# CSRF trusted origins - ADD YOUR DOMAIN HERE
CSRF_TRUSTED_ORIGINS = [
    'https://vms-backend-drf-avdygnb6afcchbhg.centralindia-01.azurewebsites.net',
    'https://*.azurewebsites.net',
]

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Ensure WhiteNoise is in middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
