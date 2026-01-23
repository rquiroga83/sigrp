"""
URL patterns for standups app.
"""
from django.urls import path
from . import views

app_name = 'standups'

urlpatterns = [
    path('', views.standup_list, name='list'),
    path('create/', views.standup_create, name='create'),
]
