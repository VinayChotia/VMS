# visitor_management/wsgi.py

import os

# Set settings module FIRST
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "visitor_management.settings")
environment = os.environ.get('DJANGO_ENV', 'production')

if environment == 'development':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_management.settings.development')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_management.settings.production')

# Now import Django
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()