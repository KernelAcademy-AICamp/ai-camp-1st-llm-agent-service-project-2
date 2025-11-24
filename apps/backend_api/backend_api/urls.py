"""
Backend API URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.v1.urls')),
    path('api/v1/cases/', include('cases.urls')),  # Case CRUD API
    path('api/v1/documents/', include('documents.urls')),  # Document CRUD API
    path('api/v1/', include('organizations.urls')),  # Organization & Project CRUD API
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
