"""
WSGI config para Gunicorn / produção.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RTT_IT_System.settings')

application = get_wsgi_application()
