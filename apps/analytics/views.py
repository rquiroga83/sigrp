"""
Views for analytics app.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def dashboard(request):
    """Dashboard principal con métricas clave."""
    return render(request, 'analytics/dashboard.html')


@login_required
def projects_report(request):
    """Reporte de proyectos."""
    return render(request, 'analytics/projects_report.html')


@login_required
def resources_report(request):
    """Reporte de recursos."""
    return render(request, 'analytics/resources_report.html')
