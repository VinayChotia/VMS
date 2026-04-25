# visitor_management/asgi.py

import os

# Set settings module FIRST
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_management.settings')
environment = os.environ.get('DJANGO_ENV', 'production')

if environment == 'development':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_management.settings.development')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visitor_management.settings.production')

# Get ASGI application FIRST - this initializes Django
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()  # This loads Django apps

# Now import channels and your app modules (after Django is ready)
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from notification import routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns
            )
        )
    ),
})