"""
URL patterns for resources app.
"""
from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    path('', views.resource_list, name='list'),
    path('<int:pk>/', views.resource_detail, name='detail'),
]
