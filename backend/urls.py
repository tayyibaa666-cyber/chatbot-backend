"""
URL configuration for backend project.
File: backend/urls.py (or your_project_name/urls.py)

This is the CORRECTED version.
Copy this ENTIRE file to your backend/urls.py
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # API routes - Include all api.urls patterns
    # This makes ALL patterns in api/urls.py available at /api/*
    path('api/', include('api.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)