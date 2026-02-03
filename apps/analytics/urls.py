"""
URL patterns for analytics app.
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('resources/', views.resources_utilization, name='resources_utilization'),
    path('resource-booking/', views.resource_booking, name='resource_booking'),
    path('financial/', views.financial_report, name='financial_report'),
    path('team-mood/', views.team_mood, name='team_mood'),
]
