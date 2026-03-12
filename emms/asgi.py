"""
ASGI config for emms project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Point the ASGI entrypoint at the shared project settings module.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emms.settings')

application = get_asgi_application()


