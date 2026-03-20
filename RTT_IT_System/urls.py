"""
URLconf principal: app RTT, API, backoffice, admin, PWA e healthcheck.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from rtt import views as rtt_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', rtt_views.health_view, name='health'),
    path('manifest.webmanifest', rtt_views.manifest_view, name='manifest'),
    path('service-worker.js', rtt_views.service_worker_view, name='service_worker'),
    path('', rtt_views.root_view, name='root'),
    path('area/', rtt_views.area_utilizador_view, name='area_utilizador'),
    path('api/', include('rtt.urls')),
    path('backoffice/', include('rtt.backoffice_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
