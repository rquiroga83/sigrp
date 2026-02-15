"""
URL patterns for projects app.
"""
from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='list'),
    path('create/', views.project_create, name='create'),
    path('<int:pk>/', views.project_detail, name='detail'),
    path('<int:pk>/edit/', views.project_edit, name='edit'),
    path('<int:pk>/assign-resources/', views.assign_resources, name='assign_resources'),
    path('<int:pk>/manage-allocations/', views.manage_allocations, name='manage_allocations'),
    
    # RF-11: Motor de Validación de Asignaciones
    path('check-availability/', views.check_resource_availability, name='check_availability'),
    path('<int:pk>/allocation/create/', views.create_allocation, name='create_allocation'),
    path('allocation/<int:allocation_id>/delete/', views.delete_allocation, name='delete_allocation'),
    
    # TimeLogs - Registro de Horas
    path('timelogs/', views.my_timelogs, name='my_timelogs'),
    path('timelogs/create/', views.create_timelog, name='create_timelog'),
    path('timelogs/<int:pk>/edit/', views.edit_timelog, name='edit_timelog'),
    path('timelogs/<int:pk>/delete/', views.delete_timelog, name='delete_timelog'),
    path('api/projects/<int:project_id>/tasks/', views.get_project_tasks, name='get_project_tasks'),
    
    # Actualizar estado de tarea
    path('<int:project_pk>/tasks/<int:task_pk>/update-status/', views.update_task_status, name='update_task_status'),

    # Actualizar progreso de tarea
    path('<int:project_pk>/tasks/<int:task_pk>/update-progress/', views.update_task_progress, name='update_task_progress'),
]
