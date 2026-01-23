"""
URL Configuration for SIGRP project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('resources/', include('apps.resources.urls')),
    path('projects/', include('apps.projects.urls')),
    path('standups/', include('apps.standups.urls')),
    path('analytics/', include('apps.analytics.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Personalización del Admin
admin.site.site_header = "SIGRP - Administración"
admin.site.site_title = "SIGRP Admin"
admin.site.index_title = "Gestión de Recursos y Proyectos"
