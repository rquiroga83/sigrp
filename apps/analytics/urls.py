"""
URL patterns for analytics app.
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('projects/', views.projects_report, name='projects'),
    path('resources/', views.resources_report, name='resources'),
]
