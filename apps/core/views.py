"""
Core views - Home y páginas generales.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def home(request):
    """Vista principal del sistema."""
    return render(request, 'core/home.html')
