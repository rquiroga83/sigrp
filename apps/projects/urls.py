"""
URL patterns for projects app.
"""
from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='list'),
    path('<int:pk>/', views.project_detail, name='detail'),
    path('<int:pk>/assign-resources/', views.assign_resources, name='assign_resources'),
    
    # RF-11: Motor de Validación de Asignaciones
    path('check-availability/', views.check_resource_availability, name='check_availability'),
]
