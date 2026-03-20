"""
ASGI config (opcional; produção usa WSGI).
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RTT_IT_System.settings')

application = get_asgi_application()
