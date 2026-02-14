"""
URL patterns for resources app.
"""
from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    path('', views.resource_list, name='list'),
    path('create/', views.resource_create, name='create'),
    path('capacity/', views.resource_capacity_chart, name='capacity_chart'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('<int:pk>/', views.resource_detail, name='detail'),
    path('<int:pk>/edit/', views.resource_edit, name='edit'),
]
