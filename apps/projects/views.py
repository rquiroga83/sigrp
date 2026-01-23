"""
Views for projects app.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def project_list(request):
    """Lista de proyectos."""
    return render(request, 'projects/list.html')


@login_required
def project_detail(request, pk):
    """Detalle de un proyecto."""
    return render(request, 'projects/detail.html', {'project_id': pk})
